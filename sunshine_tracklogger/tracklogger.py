#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sunshine live Track-Logger
==========================
Lauscht am sunshine live Stream (Standard: Channel "Techno") und protokolliert
alle gespielten Tracks in eine SQLite-Datenbank. Solange das Programm laeuft,
werden die Titel gesammelt - man muss den Stream nicht anhoeren.

Zusaetzlich gibt es eine lokale Web-App (http://localhost:8765) mit
Live-Trackliste, eingebautem Player fuer den Channel, Favoriten,
Statistiken und YouTube-Suchlink pro Track.

Benoetigt NUR die Python-Standardbibliothek (Python 3.8+), keine Installation.

Beispiele:
    python tracklogger.py                     # Channel "Techno", Web-UI an
    python tracklogger.py --channel trance    # anderer Channel
    python tracklogger.py --poll 60           # Sparmodus: alle 60s kurz nachschauen
    python tracklogger.py --export csv        # bisherige Tracks als CSV exportieren
    python tracklogger.py --no-web            # nur Konsole, keine Webseite
"""

import argparse
import csv
import io
import json
import re
import signal
import socket
import sqlite3
import ssl
import sys
import threading
import time
import urllib.parse
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tracks.db"

STREAM_TEMPLATE = "http://stream.sunshine-live.de/{channel}/mp3-192/stream.sunshine-live.de/"

# Bekannte Channel-Slugs (Auswahl). Es funktioniert jeder gueltige Slug von
# https://www.sunshine-live.de/music/channels - einfach per --channel angeben.
KNOWN_CHANNELS = [
    "live", "techno", "melodic-techno", "trance", "house", "classics",
    "hardstyle", "eurodance", "90er", "2000er", "hands-up", "deep-house",
]

USER_AGENT = "SunshineTrackLogger/1.0 (privater Track-Logger)"

stop_event = threading.Event()
# Web-UI kann Channel/Aufnahme umschalten -> Logger verbindet sich neu.
restart_event = threading.Event()

# Wird in main() gesetzt, von der Web-UI gelesen und geaendert.
CONFIG = {"channel": "techno", "stream_url": "", "started": None,
          "record": False, "record_dir": None, "poll": 0}


# ---------------------------------------------------------------- Datenbank

def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tracks (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               ts TEXT NOT NULL,
               channel TEXT NOT NULL,
               artist TEXT,
               title TEXT,
               raw TEXT NOT NULL
           )"""
    )
    try:
        conn.execute("ALTER TABLE tracks ADD COLUMN favorite INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Spalte existiert schon
    conn.commit()
    return conn


def last_raw(conn, channel):
    row = conn.execute(
        "SELECT raw FROM tracks WHERE channel=? ORDER BY id DESC LIMIT 1",
        (channel,),
    ).fetchone()
    return row[0] if row else None


def insert_track(conn, channel, artist, title, raw):
    conn.execute(
        "INSERT INTO tracks (ts, channel, artist, title, raw) VALUES (?,?,?,?,?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), channel, artist, title, raw),
    )
    conn.commit()


# ---------------------------------------------------------- ICY-Metadaten

def parse_stream_title(meta_block):
    """Extrahiert StreamTitle='...' aus einem ICY-Metadatenblock."""
    text = meta_block.rstrip(b"\x00").decode("utf-8", errors="replace")
    m = re.search(r"StreamTitle='(.*?)';", text)
    if not m:
        return None
    return m.group(1).strip()


def split_artist_title(raw):
    if " - " in raw:
        artist, title = raw.split(" - ", 1)
        return artist.strip(), title.strip()
    return None, raw.strip()


def open_icy_stream(url, timeout=15, max_redirects=5):
    """Oeffnet den Stream per Raw-Socket (ICY-faehig) und liefert
    (socket_file, metaint). Folgt Redirects."""
    for _ in range(max_redirects):
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        sock = socket.create_connection((host, port), timeout=timeout)
        if parsed.scheme == "https":
            ctx = ssl.create_default_context()
            sock = ctx.wrap_socket(sock, server_hostname=host)

        request = (
            f"GET {path} HTTP/1.0\r\n"
            f"Host: {host}\r\n"
            f"User-Agent: {USER_AGENT}\r\n"
            f"Icy-MetaData: 1\r\n"
            f"Accept: */*\r\n"
            f"Connection: close\r\n\r\n"
        )
        sock.sendall(request.encode("ascii"))

        f = sock.makefile("rb")
        status_line = f.readline().decode("latin-1", errors="replace").strip()
        headers = {}
        while True:
            line = f.readline()
            if not line or line in (b"\r\n", b"\n"):
                break
            if b":" in line:
                k, v = line.split(b":", 1)
                headers[k.decode("latin-1").strip().lower()] = (
                    v.decode("latin-1").strip()
                )

        status_parts = status_line.split()
        status_code = int(status_parts[1]) if len(status_parts) > 1 else 0

        if status_code in (301, 302, 303, 307, 308) and "location" in headers:
            f.close()
            sock.close()
            url = urllib.parse.urljoin(url, headers["location"])
            continue

        if status_code != 200:
            f.close()
            sock.close()
            raise ConnectionError(f"Stream antwortet mit: {status_line}")

        metaint = headers.get("icy-metaint")
        if not metaint:
            f.close()
            sock.close()
            raise ConnectionError(
                "Server liefert keine ICY-Metadaten (icy-metaint fehlt)."
            )
        return f, sock, int(metaint)

    raise ConnectionError("Zu viele Redirects.")


def read_exact(f, n):
    """Liest genau n Bytes oder wirft ConnectionError bei Streamende."""
    buf = b""
    while len(buf) < n:
        chunk = f.read(n - len(buf))
        if not chunk:
            raise ConnectionError("Stream wurde beendet.")
        buf += chunk
    return buf


def iter_stream_titles(url, single_shot=False, recorder=None,
                       abort_event=None):
    """Generator: liefert jeden StreamTitle, sobald er sich im Stream aendert.
    Bei single_shot=True wird nur der erste gefundene Titel geliefert.
    Mit recorder werden die Audiodaten mitgeschnitten statt verworfen.
    abort_event beendet die Schleife sauber (z.B. bei Channel-Wechsel)."""
    f, sock, metaint = open_icy_stream(url)
    try:
        while not stop_event.is_set() and not (
                abort_event and abort_event.is_set()):
            audio = read_exact(f, metaint)
            if recorder:
                recorder.write(audio)
            length = read_exact(f, 1)[0] * 16
            if length:
                title = parse_stream_title(read_exact(f, length))
                if title:
                    yield title
                    if single_shot:
                        return
    finally:
        try:
            f.close()
        except OSError:
            pass
        try:
            sock.close()
        except OSError:
            pass


def is_station_promo(artist, title, raw):
    """Jingles/Eigenwerbung des Senders aussortieren."""
    check = (artist or raw).lower()
    return check.startswith("sunshine live") or check.startswith("sunshine-live")


# ---------------------------------------------------------------- Recorder

class Recorder:
    """Schneidet den Stream mit und legt pro Track eine eigene MP3-Datei an.
    Dateiname: 'HH-MM Artist - Titel.mp3'. Angeschnittene Tracks (Anfang
    oder Ende fehlt, z.B. beim Start oder bei Verbindungsabbruch) bekommen
    den Zusatz '(angeschnitten)'."""

    def __init__(self, directory):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.f = None
        self.raw = None
        self.partial = False
        self.part_path = None

    @staticmethod
    def _safe_name(text):
        text = re.sub(r'[\\/:*?"<>|]', "_", text)
        return text.strip()[:150] or "unbenannt"

    def write(self, data):
        if self.f:
            self.f.write(data)

    def start_track(self, raw, save=True, partial=False):
        """Aktuellen Track abschliessen und (falls save) neue Datei beginnen."""
        self.finish()
        if not save:
            return
        self.raw = raw
        self.partial = partial
        stamp = datetime.now().strftime("%Y-%m-%d %H-%M")
        self.part_path = self.dir / f"{stamp} {self._safe_name(raw)}.mp3.part"
        self.f = open(self.part_path, "wb")

    def finish(self, partial_end=False):
        """Datei schliessen und final benennen."""
        if not self.f:
            return
        self.f.close()
        self.f = None
        final = self.part_path.with_suffix("")  # entfernt ".part" -> .mp3
        if self.partial or partial_end:
            final = final.with_name(final.stem + " (angeschnitten).mp3")
        n = 2
        while final.exists():
            final = final.with_name(f"{final.stem} ({n}).mp3")
            n += 1
        try:
            self.part_path.replace(final)
            size_mb = final.stat().st_size / 1e6
            print(f"  gespeichert: {final.name} ({size_mb:.1f} MB)")
        except OSError as exc:
            print(f"  Speichern fehlgeschlagen: {exc}")
        self.part_path = None
        self.raw = None
        self.partial = False


# ------------------------------------------------------------------ Logger

def log_title(conn, channel, raw, quiet_promos=True):
    """Schreibt einen Titel in die DB, wenn er neu ist. Rueckgabe: bool."""
    if raw == last_raw(conn, channel):
        return False
    artist, title = split_artist_title(raw)
    if quiet_promos and is_station_promo(artist, title, raw):
        print(f"  (Jingle/Werbung uebersprungen: {raw})")
        return False
    insert_track(conn, channel, artist, title, raw)
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {raw}")
    return True


def run_logger(poll_interval=0):
    conn = db_connect()
    backoff = 2
    print(f"Datenbank: {DB_PATH}")
    if poll_interval:
        print(f"Sparmodus: alle {poll_interval}s wird kurz nachgeschaut.\n")
    else:
        print("Dauerbetrieb: jeder Trackwechsel wird sofort erfasst.\n")

    last_seen = None
    last_channel = None
    last_record = None
    while not stop_event.is_set():
        # Einstellungen koennen von der Web-UI geaendert worden sein.
        channel = CONFIG["channel"]
        url = CONFIG["stream_url"]
        if channel != last_channel:
            print(f"Logge Channel '{channel}'  ->  {url}")
            last_channel = channel
            last_seen = None
        recorder = None
        if CONFIG["record"] and not poll_interval:
            recorder = Recorder(CONFIG["record_dir"] or
                                BASE_DIR / "recordings" / channel)
        if bool(recorder) != last_record:
            print(f"Aufnahme {'AN: MP3s landen in ' + str(recorder.dir) if recorder else 'AUS'}")
            last_record = bool(recorder)
        restart_event.clear()
        try:
            if poll_interval:
                for raw in iter_stream_titles(url, single_shot=True):
                    if raw != last_seen:
                        log_title(conn, channel, raw)
                        last_seen = raw
                backoff = 2
                waited = 0
                while (waited < poll_interval and not stop_event.is_set()
                       and not restart_event.is_set()):
                    stop_event.wait(1)
                    waited += 1
            else:
                fresh = True  # erster Titel nach (Re-)Connect ist angeschnitten
                for raw in iter_stream_titles(url, recorder=recorder,
                                              abort_event=restart_event):
                    if recorder and (fresh or raw != last_seen):
                        artist, title = split_artist_title(raw)
                        recorder.start_track(
                            raw,
                            save=not is_station_promo(artist, title, raw),
                            partial=fresh,
                        )
                    fresh = False
                    if raw != last_seen:
                        log_title(conn, channel, raw)
                        last_seen = raw
                    backoff = 2
        except (OSError, ConnectionError) as exc:
            if stop_event.is_set():
                break
            print(f"Verbindungsproblem: {exc} - neuer Versuch in {backoff}s ...")
            stop_event.wait(backoff)
            backoff = min(backoff * 2, 60)
        finally:
            if recorder:
                recorder.finish(partial_end=True)
    conn.close()
    print("Logger beendet.")


# ------------------------------------------------------------------ Web-UI

PAGE = r"""<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>sunshine live Track-Logger</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='24' fill='%23ffc233'/%3E%3Ctext x='50' y='72' font-size='58' text-anchor='middle'%3E%26%239835;%3C/text%3E%3C/svg%3E">
<style>
  :root {
    color-scheme: dark;
    --bg: #0c0e12; --surface: #14171d; --surface2: #1b1f27;
    --border: #262b35; --border2: #313848;
    --ink: #e9ecf2; --ink2: #9aa3b2; --muted: #667085;
    --accent: #ffc233; --accent2: #ffd166; --accent-ink: #1a1400;
  }
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
         background: var(--bg); color: var(--ink); margin: 0;
         -webkit-font-smoothing: antialiased; }
  .wrap { max-width: 1100px; margin: 0 auto; padding: 1.2rem 1.2rem 3rem; }

  /* ---------- Kopf ---------- */
  header { display: flex; align-items: center; gap: .7rem; padding: .3rem 0 1.1rem; }
  .logo { width: 34px; height: 34px; border-radius: 10px; flex: none;
          background: linear-gradient(135deg, var(--accent), #ff8a2b);
          display: grid; place-items: center; color: var(--accent-ink);
          font-weight: 800; font-size: 1.05rem; cursor: pointer;
          user-select: none; -webkit-user-select: none; }
  .logo:active { transform: scale(.92); }
  h1 { font-size: 1.05rem; margin: 0; font-weight: 650; letter-spacing: .01em; }
  .sub { color: var(--ink2); font-size: .8rem; margin-top: .1rem; }
  .badge { margin-left: auto; background: var(--surface2); border: 1px solid var(--border);
           color: var(--accent); padding: .3rem .7rem; border-radius: 999px;
           font-size: .78rem; font-weight: 600; text-transform: uppercase;
           letter-spacing: .06em; white-space: nowrap; }

  /* ---------- Player / Now Playing ---------- */
  .player { background: linear-gradient(180deg, var(--surface2), var(--surface));
            border: 1px solid var(--border); border-radius: 16px;
            padding: 1.1rem 1.2rem; display: flex; align-items: center;
            gap: 1.1rem; flex-wrap: wrap; }
  .playbtn { width: 56px; height: 56px; border-radius: 50%; border: none; flex: none;
             background: var(--accent); color: var(--accent-ink); cursor: pointer;
             display: grid; place-items: center; transition: transform .12s, background .12s; }
  .playbtn:hover { background: var(--accent2); transform: scale(1.05); }
  .playbtn svg { width: 22px; height: 22px; }
  .now { flex: 1 1 14rem; min-width: 0; }
  .now .label { font-size: .72rem; font-weight: 600; letter-spacing: .1em;
                text-transform: uppercase; color: var(--ink2);
                display: flex; align-items: center; gap: .5rem; }
  .now .track { font-size: 1.25rem; font-weight: 650; margin-top: .25rem;
                overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .now .since { color: var(--muted); font-size: .8rem; margin-top: .15rem; }
  .eq { display: inline-flex; gap: 2px; align-items: flex-end; height: 12px; }
  .eq i { width: 3px; background: var(--accent); border-radius: 1px;
          animation: eq 1s ease-in-out infinite; }
  .eq i:nth-child(2) { animation-delay: .2s; } .eq i:nth-child(3) { animation-delay: .4s; }
  .eq i:nth-child(4) { animation-delay: .1s; }
  .eq.off i { animation-play-state: paused; height: 3px !important; }
  @keyframes eq { 0%,100% { height: 3px; } 50% { height: 12px; } }
  .vol { display: flex; align-items: center; gap: .5rem; color: var(--ink2); }
  .vol input { accent-color: var(--accent); width: 110px; }
  .now-actions { display: flex; gap: .5rem; }
  .ctl { display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; }
  select { border: 1px solid var(--border2); background: var(--surface2);
           color: var(--ink); border-radius: 999px; padding: .42rem .7rem;
           font-size: .82rem; cursor: pointer; outline: none; }
  select:focus { border-color: var(--accent); }
  .chip.rec.on { background: #e5484d; border-color: #e5484d; color: #fff;
                 font-weight: 700; animation: recpulse 1.6s ease-in-out infinite; }
  @keyframes recpulse { 0%,100% { opacity: 1; } 50% { opacity: .65; } }

  /* ---------- Stat-Kacheln ---------- */
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
           gap: .8rem; margin: 1rem 0; }
  .tile { background: var(--surface); border: 1px solid var(--border);
          border-radius: 14px; padding: .85rem 1rem; }
  .tile .label { color: var(--ink2); font-size: .78rem; }
  .tile .value { font-size: 1.55rem; font-weight: 600; margin-top: .15rem; }

  /* ---------- Layout ---------- */
  .cols { display: grid; grid-template-columns: 2fr 1fr; gap: .9rem; align-items: start; }
  @media (max-width: 820px) { .cols { grid-template-columns: 1fr; } }
  .card { background: var(--surface); border: 1px solid var(--border);
          border-radius: 14px; overflow: hidden; }
  .card h2 { font-size: .85rem; font-weight: 650; margin: 0; padding: .9rem 1rem .6rem;
             color: var(--ink2); text-transform: uppercase; letter-spacing: .07em; }

  /* ---------- Toolbar ---------- */
  .toolbar { display: flex; gap: .6rem; padding: .9rem 1rem .7rem; flex-wrap: wrap;
             align-items: center; }
  .toolbar input[type=search] { flex: 1 1 12rem; padding: .5rem .75rem;
      border-radius: 9px; border: 1px solid var(--border2); background: var(--surface2);
      color: var(--ink); font-size: .9rem; outline: none; }
  .toolbar input[type=search]:focus { border-color: var(--accent); }
  .chip { border: 1px solid var(--border2); background: var(--surface2); color: var(--ink2);
          border-radius: 999px; padding: .42rem .85rem; font-size: .82rem;
          cursor: pointer; transition: all .12s; white-space: nowrap; }
  .chip:hover { color: var(--ink); }
  .chip.on { background: var(--accent); border-color: var(--accent);
             color: var(--accent-ink); font-weight: 600; }

  /* ---------- Trackliste ---------- */
  .datehdr { padding: .55rem 1rem .35rem; color: var(--muted); font-size: .74rem;
             font-weight: 650; text-transform: uppercase; letter-spacing: .08em;
             border-top: 1px solid var(--border); background: rgba(255,255,255,.015); }
  .row { display: flex; align-items: center; gap: .6rem; padding: .5rem 1rem;
         border-top: 1px solid var(--border); }
  .row:hover { background: var(--surface2); }
  .row .t { color: var(--muted); font-size: .78rem; width: 3.2rem; flex: none;
            font-variant-numeric: tabular-nums; }
  .row .name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis;
               white-space: nowrap; font-size: .92rem; }
  .row .name b { font-weight: 600; }
  .row .name span { color: var(--ink2); }
  .iconbtn { border: none; background: none; color: var(--muted); cursor: pointer;
             padding: .3rem; border-radius: 7px; display: grid; place-items: center;
             transition: color .12s, background .12s; flex: none; }
  .iconbtn:hover { color: var(--ink); background: var(--surface2); }
  .iconbtn svg { width: 17px; height: 17px; }
  .iconbtn.fav { color: var(--accent); }
  .empty { padding: 1.6rem 1rem; color: var(--muted); font-size: .88rem; }

  /* ---------- Top Artists ---------- */
  .bars { padding: .2rem 1rem 1rem; }
  .bar { margin-top: .65rem; }
  .bar .meta { display: flex; justify-content: space-between; font-size: .82rem;
               margin-bottom: .3rem; }
  .bar .meta .n { color: var(--ink2); font-variant-numeric: tabular-nums; }
  .bar .track-bg { height: 6px; border-radius: 4px; background: var(--surface2); }
  .bar .fill { height: 6px; border-radius: 4px; background: var(--accent);
               min-width: 6px; transition: width .4s ease; }

  footer { color: var(--muted); font-size: .75rem; text-align: center; margin-top: 1.6rem; }
  a { color: var(--accent2); }
  .toast { position: fixed; bottom: 1.2rem; left: 50%; transform: translateX(-50%);
           background: var(--surface2); border: 1px solid var(--border2);
           padding: .55rem 1rem; border-radius: 10px; font-size: .85rem;
           opacity: 0; pointer-events: none; transition: opacity .25s; }
  .toast.show { opacity: 1; }
</style></head><body>
<div class="wrap">
  <header>
    <div class="logo">&#9835;</div>
    <div>
      <h1>sunshine live &middot; Track-Logger</h1>
      <div class="sub" id="statusline">verbinde ...</div>
    </div>
    <div class="badge" id="channel">&nbsp;</div>
  </header>

  <div class="player">
    <button class="playbtn" id="playbtn" title="Channel abspielen" aria-label="Abspielen">
      <svg id="ic-play" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
      <svg id="ic-pause" viewBox="0 0 24 24" fill="currentColor" style="display:none">
        <path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>
    </button>
    <div class="now">
      <div class="label"><span class="eq off" id="eq"><i></i><i></i><i></i><i></i></span>
        L&auml;uft gerade</div>
      <div class="track" id="nowtrack">&ndash;</div>
      <div class="since" id="nowsince"></div>
    </div>
    <div class="now-actions">
      <button class="iconbtn" id="nowyt" title="Aktuellen Track auf YouTube suchen">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M21.6 7.2a2.8 2.8 0 0 0-2-2C17.9 4.8 12 4.8 12 4.8s-5.9 0-7.6.4a2.8 2.8 0 0 0-2 2A29 29 0 0 0 2 12a29 29 0 0 0 .4 4.8 2.8 2.8 0 0 0 2 2c1.7.4 7.6.4 7.6.4s5.9 0 7.6-.4a2.8 2.8 0 0 0 2-2A29 29 0 0 0 22 12a29 29 0 0 0-.4-4.8zM9.8 15.3V8.7l5.7 3.3z"/></svg>
      </button>
    </div>
    <div class="vol">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3a4.5 4.5 0 0 0-2.5-4v8a4.5 4.5 0 0 0 2.5-4z"/></svg>
      <input type="range" id="vol" min="0" max="100" value="80">
    </div>
    <div class="ctl">
      <select id="chsel" title="Channel wechseln"></select>
      <button class="chip rec" id="recbtn"
        title="Aufnahme: jeder Track wird als eigene MP3 gespeichert">&#9679; REC</button>
    </div>
  </div>

  <div class="stats">
    <div class="tile"><div class="label">Heute</div><div class="value" id="st-today">&ndash;</div></div>
    <div class="tile"><div class="label">Gesamt</div><div class="value" id="st-total">&ndash;</div></div>
    <div class="tile"><div class="label">Interpreten</div><div class="value" id="st-artists">&ndash;</div></div>
    <div class="tile"><div class="label">Favoriten</div><div class="value" id="st-favs">&ndash;</div></div>
  </div>

  <div class="cols">
    <div class="card">
      <div class="toolbar">
        <input type="search" id="filter" placeholder="Filtern: Artist oder Titel ...">
        <button class="chip" id="favonly">&#9733; Nur Favoriten</button>
        <button class="chip" id="dl">&#8681; CSV</button>
      </div>
      <div id="list"><div class="empty">Lade Tracks ...</div></div>
    </div>
    <div class="card">
      <h2>Top Artists</h2>
      <div class="bars" id="bars"><div class="empty">Noch keine Daten.</div></div>
    </div>
  </div>

  <footer>L&auml;uft lokal &middot; Daten in <code>tracks.db</code> &middot;
    Aktualisiert sich automatisch alle 10&nbsp;Sekunden</footer>
</div>
<div class="toast" id="toast"></div>

<script>
"use strict";
let tracks = [], stats = null, favOnly = false, audio = null;

const $ = id => document.getElementById(id);
const esc = s => { const d = document.createElement("div"); d.textContent = s || ""; return d.innerHTML; };

function ytUrl(t) {
  const q = encodeURIComponent(((t.artist ? t.artist + " " : "") + (t.title || t.raw)).trim());
  return "https://www.youtube.com/results?search_query=" + q;
}
function toast(msg) {
  const el = $("toast"); el.textContent = msg; el.classList.add("show");
  clearTimeout(toast._t); toast._t = setTimeout(() => el.classList.remove("show"), 1800);
}
function parseTs(ts) { return new Date(ts.replace(" ", "T")); }
function relTime(ts) {
  const s = Math.max(0, (Date.now() - parseTs(ts)) / 1000);
  if (s < 90) return "gerade eben";
  if (s < 3600) return "vor " + Math.round(s / 60) + " min";
  if (s < 86400) return "vor " + Math.round(s / 3600) + " h";
  return "am " + ts.slice(0, 10);
}
function dayLabel(ts) {
  const d = ts.slice(0, 10);
  const today = new Date(), yest = new Date(Date.now() - 864e5);
  const fmt = x => x.toISOString ? x.toLocaleDateString("sv-SE") : x;
  if (d === fmt(today)) return "Heute";
  if (d === fmt(yest)) return "Gestern";
  return parseTs(ts).toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long" });
}

/* ---------------- Player ---------------- */
let curStream = null;
function initPlayer(url) {
  if (!url) return;
  if (!audio) {
    audio = new Audio();
    audio.preload = "none";
    audio.volume = $("vol").value / 100;
    audio.addEventListener("playing", () => setPlaying(true));
    audio.addEventListener("pause", () => setPlaying(false));
    audio.addEventListener("error", () => { setPlaying(false); toast("Stream konnte nicht abgespielt werden"); });
    audio.src = url;
    curStream = url;
  } else if (url !== curStream) {
    // Channel wurde gewechselt: Player umziehen, Wiedergabe fortsetzen
    const wasPlaying = !audio.paused;
    audio.pause();
    audio.src = url;
    curStream = url;
    if (wasPlaying) { audio.load(); audio.play().catch(() => {}); }
  }
}
function setPlaying(on) {
  $("ic-play").style.display = on ? "none" : "";
  $("ic-pause").style.display = on ? "" : "none";
  $("eq").classList.toggle("off", !on);
  $("playbtn").title = on ? "Pause" : "Channel abspielen";
}
$("playbtn").addEventListener("click", () => {
  if (!audio) { toast("Stream-URL noch nicht geladen"); return; }
  if (audio.paused) {
    // Live-Stream: beim Fortsetzen neu laden, damit es LIVE ist (kein alter Puffer)
    audio.load();
    audio.play().catch(() => toast("Wiedergabe blockiert - bitte nochmal klicken"));
  } else {
    audio.pause();
  }
});
$("vol").addEventListener("input", e => { if (audio) audio.volume = e.target.value / 100; });

/* ---------------- Rendering ---------------- */
const SVG_STAR = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 17.3 6.2 21l1.6-6.6L2.5 9.9l6.8-.6L12 3l2.7 6.3 6.8.6-5.3 4.5L17.8 21z"/></svg>';
const SVG_STAR_O = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 17.3 6.2 21l1.6-6.6L2.5 9.9l6.8-.6L12 3l2.7 6.3 6.8.6-5.3 4.5L17.8 21z"/></svg>';
const SVG_YT = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M21.6 7.2a2.8 2.8 0 0 0-2-2C17.9 4.8 12 4.8 12 4.8s-5.9 0-7.6.4a2.8 2.8 0 0 0-2 2A29 29 0 0 0 2 12a29 29 0 0 0 .4 4.8 2.8 2.8 0 0 0 2 2c1.7.4 7.6.4 7.6.4s5.9 0 7.6-.4a2.8 2.8 0 0 0 2-2A29 29 0 0 0 22 12a29 29 0 0 0-.4-4.8zM9.8 15.3V8.7l5.7 3.3z"/></svg>';
const SVG_COPY = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>';

function render() {
  const f = $("filter").value.toLowerCase();
  const rows = tracks.filter(t =>
    (!favOnly || t.favorite) &&
    (!f || (t.raw || "").toLowerCase().includes(f)));

  let html = "", lastDay = null;
  for (const t of rows) {
    const day = t.ts.slice(0, 10);
    if (day !== lastDay) { html += `<div class="datehdr">${esc(dayLabel(t.ts))}</div>`; lastDay = day; }
    const name = t.artist
      ? `<b>${esc(t.artist)}</b> <span>&ndash; ${esc(t.title)}</span>`
      : esc(t.raw);
    html += `<div class="row">
      <div class="t">${t.ts.slice(11, 16)}</div>
      <div class="name" title="${esc(t.raw)}">${name}</div>
      <button class="iconbtn${t.favorite ? " fav" : ""}" data-fav="${t.id}"
        title="${t.favorite ? "Favorit entfernen" : "Als Favorit merken"}">
        ${t.favorite ? SVG_STAR : SVG_STAR_O}</button>
      <button class="iconbtn" data-copy="${esc(t.raw)}" title="Track kopieren">${SVG_COPY}</button>
      <a class="iconbtn" href="${ytUrl(t)}" target="_blank" rel="noopener"
        title="Auf YouTube suchen">${SVG_YT}</a>
    </div>`;
  }
  $("list").innerHTML = html ||
    `<div class="empty">${favOnly ? "Noch keine Favoriten - Stern bei einem Track anklicken." : "Noch keine Tracks erfasst. Sobald ein neuer Track läuft, erscheint er hier."}</div>`;
}

function renderNow() {
  const t = tracks[0];
  if (!t) { $("nowtrack").textContent = "Warte auf den ersten Track ..."; $("nowsince").textContent = ""; return; }
  $("nowtrack").textContent = t.raw;
  $("nowsince").textContent = "erfasst " + relTime(t.ts);
  $("nowyt").onclick = () => window.open(ytUrl(t), "_blank");
}

function renderStats() {
  if (!stats) return;
  $("st-today").textContent = stats.today;
  $("st-total").textContent = stats.total;
  $("st-artists").textContent = stats.artists;
  $("st-favs").textContent = stats.favorites;
  $("channel").textContent = stats.channel;
  let line = "Logger aktiv · " + stats.total + " Tracks in der Datenbank";
  if (stats.record) {
    line += " · ● Aufnahme läuft";
    if (stats.rec_files) line += " (" + stats.rec_files + " MP3s, " + stats.rec_mb + " MB)";
  }
  $("statusline").textContent = line;

  const sel = $("chsel");
  if (!sel.options.length) {
    const chans = (stats.channels || []).slice();
    if (!chans.includes(stats.channel)) chans.unshift(stats.channel);
    sel.innerHTML = chans.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
  }
  if (document.activeElement !== sel) sel.value = stats.channel;
  $("recbtn").classList.toggle("on", !!stats.record);
  updateRecVisibility();

  initPlayer(stats.stream_url);

  const top = stats.top_artists || [];
  if (top.length) {
    const max = top[0][1];
    $("bars").innerHTML = top.map(([name, n]) => `
      <div class="bar">
        <div class="meta"><span>${esc(name)}</span><span class="n">${n}</span></div>
        <div class="track-bg"><div class="fill" style="width:${Math.round(100 * n / max)}%"></div></div>
      </div>`).join("");
  }
}

/* ---------------- Geheimschalter (5x aufs Logo klicken) ---------------- */
let recUnlocked = localStorage.getItem("recUnlocked") === "1";
let logoClicks = [];
function updateRecVisibility() {
  // Sichtbar nur, wenn freigeschaltet - oder Aufnahme bereits laeuft
  // (sonst koennte man sie nicht mehr ausschalten).
  const show = stats && stats.record_possible && (recUnlocked || stats.record);
  $("recbtn").style.display = show ? "" : "none";
}
document.querySelector(".logo").addEventListener("click", () => {
  const now = Date.now();
  logoClicks = logoClicks.filter(t => now - t < 3000);
  logoClicks.push(now);
  if (logoClicks.length >= 5) {
    logoClicks = [];
    recUnlocked = !recUnlocked;
    localStorage.setItem("recUnlocked", recUnlocked ? "1" : "0");
    toast(recUnlocked ? "🎛️ Geheimschalter gefunden: Aufnahme freigeschaltet!"
                      : "Aufnahme-Schalter wieder versteckt");
    updateRecVisibility();
  }
});

/* ---------------- Events ---------------- */
$("filter").addEventListener("input", render);
$("favonly").addEventListener("click", () => {
  favOnly = !favOnly; $("favonly").classList.toggle("on", favOnly); render();
});
$("dl").addEventListener("click", () => { location.href = "/export.csv"; });
async function postSettings(body) {
  try {
    const r = await fetch("/api/settings", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body) });
    const d = await r.json().catch(() => ({}));
    if (d.error) { toast(d.error); return null; }
    return d;
  } catch (_) { toast("Keine Verbindung zum Logger"); return null; }
}
$("chsel").addEventListener("change", async e => {
  const d = await postSettings({ channel: e.target.value });
  if (d) { toast("Wechsle zu Channel: " + d.channel + " ..."); setTimeout(load, 1500); }
});
$("recbtn").addEventListener("click", async () => {
  const d = await postSettings({ record: !(stats && stats.record) });
  if (d) {
    toast(d.record ? "Aufnahme AN – jeder Track wird als MP3 gespeichert"
                   : "Aufnahme AUS");
    setTimeout(load, 800);
  }
});
$("list").addEventListener("click", async e => {
  const favBtn = e.target.closest("[data-fav]");
  const copyBtn = e.target.closest("[data-copy]");
  if (favBtn) {
    const id = +favBtn.dataset.fav;
    const t = tracks.find(x => x.id === id);
    const fav = t.favorite ? 0 : 1;
    t.favorite = fav;
    render();
    try {
      await fetch("/api/favorite", { method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, fav }) });
      if (stats) { stats.favorites += fav ? 1 : -1; $("st-favs").textContent = stats.favorites; }
    } catch (_) { toast("Speichern fehlgeschlagen"); }
  } else if (copyBtn) {
    try { await navigator.clipboard.writeText(copyBtn.dataset.copy); toast("Kopiert: " + copyBtn.dataset.copy); }
    catch (_) { toast("Kopieren nicht möglich"); }
  }
});

/* ---------------- Laden ---------------- */
async function load() {
  try {
    const [r1, r2] = await Promise.all([
      fetch("/api/tracks?limit=1000"), fetch("/api/stats")]);
    tracks = await r1.json();
    stats = await r2.json();
    render(); renderNow(); renderStats();
  } catch (_) {
    $("statusline").textContent = "Keine Verbindung zum Logger - läuft das Programm noch?";
  }
}
load();
setInterval(load, 10000);
setInterval(renderNow, 30000); // "vor X min" aktuell halten
</script></body></html>"""


class WebHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # keine Request-Logs in der Konsole

    def _send(self, body, ctype="application/json; charset=utf-8", extra=None):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self._send(PAGE.encode("utf-8"), "text/html; charset=utf-8")

        elif parsed.path == "/api/tracks":
            qs = urllib.parse.parse_qs(parsed.query)
            try:
                limit = min(int(qs.get("limit", ["200"])[0]), 5000)
            except ValueError:
                limit = 200
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute(
                "SELECT id, ts, channel, artist, title, raw, favorite "
                "FROM tracks ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            conn.close()
            data = [
                {"id": r[0], "ts": r[1], "channel": r[2], "artist": r[3],
                 "title": r[4], "raw": r[5], "favorite": r[6]}
                for r in rows
            ]
            self._send(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        elif parsed.path == "/api/stats":
            today = datetime.now().strftime("%Y-%m-%d")
            conn = sqlite3.connect(DB_PATH)
            total = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
            n_today = conn.execute(
                "SELECT COUNT(*) FROM tracks WHERE substr(ts,1,10)=?", (today,)
            ).fetchone()[0]
            artists = conn.execute(
                "SELECT COUNT(DISTINCT artist) FROM tracks WHERE artist IS NOT NULL"
            ).fetchone()[0]
            favorites = conn.execute(
                "SELECT COUNT(*) FROM tracks WHERE favorite=1"
            ).fetchone()[0]
            top = conn.execute(
                "SELECT artist, COUNT(*) n FROM tracks WHERE artist IS NOT NULL "
                "GROUP BY artist ORDER BY n DESC, artist LIMIT 8"
            ).fetchall()
            conn.close()
            rec_files = rec_bytes = 0
            rec_dir = Path(CONFIG["record_dir"] or
                           BASE_DIR / "recordings" / CONFIG["channel"])
            if CONFIG["record"] and rec_dir.is_dir():
                for p in rec_dir.glob("*.mp3*"):
                    try:
                        rec_bytes += p.stat().st_size
                        rec_files += 1
                    except OSError:
                        pass
            self._send(json.dumps({
                "channel": CONFIG["channel"],
                "stream_url": CONFIG["stream_url"],
                "channels": KNOWN_CHANNELS,
                "record": CONFIG["record"],
                "record_possible": not CONFIG["poll"],
                "rec_files": rec_files,
                "rec_mb": round(rec_bytes / 1e6),
                "total": total, "today": n_today, "artists": artists,
                "favorites": favorites, "top_artists": top,
            }, ensure_ascii=False).encode("utf-8"))

        elif parsed.path == "/export.csv":
            buf = io.StringIO()
            writer = csv.writer(buf, delimiter=";")
            writer.writerow(["Zeit", "Channel", "Artist", "Titel", "Favorit",
                             "YouTube-Suche"])
            conn = sqlite3.connect(DB_PATH)
            for ts, channel, artist, title, raw, fav in conn.execute(
                "SELECT ts, channel, artist, title, raw, favorite "
                "FROM tracks ORDER BY id"
            ):
                query = urllib.parse.quote_plus(
                    f"{artist or ''} {title or raw}".strip())
                writer.writerow([
                    ts, channel, artist or "", title or raw,
                    "ja" if fav else "",
                    f"https://www.youtube.com/results?search_query={query}",
                ])
            conn.close()
            body = ("\ufeff" + buf.getvalue()).encode("utf-8")
            self._send(body, "text/csv; charset=utf-8", {
                "Content-Disposition": 'attachment; filename="tracks.csv"'})

        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/favorite":
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length))
                track_id = int(payload["id"])
                fav = 1 if payload.get("fav") else 0
            except (ValueError, KeyError, json.JSONDecodeError):
                self.send_error(400)
                return
            conn = sqlite3.connect(DB_PATH)
            conn.execute("UPDATE tracks SET favorite=? WHERE id=?",
                         (fav, track_id))
            conn.commit()
            conn.close()
            self._send(b'{"ok": true}')

        elif self.path == "/api/settings":
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length))
            except (ValueError, json.JSONDecodeError):
                self.send_error(400)
                return
            if "channel" in payload:
                ch = str(payload["channel"]).strip().lower()
                if not re.fullmatch(r"[a-z0-9-]{2,40}", ch):
                    self._send(json.dumps(
                        {"error": "Ungueltiger Channel-Name."}).encode())
                    return
                CONFIG["channel"] = ch
                CONFIG["stream_url"] = STREAM_TEMPLATE.format(channel=ch)
            if "record" in payload:
                if CONFIG["poll"]:
                    self._send(json.dumps(
                        {"error": "Aufnahme geht nicht im Sparmodus "
                                  "(--poll). Ohne --poll neu starten."}
                    ).encode("utf-8"))
                    return
                CONFIG["record"] = bool(payload["record"])
            restart_event.set()
            self._send(json.dumps({
                "ok": True, "channel": CONFIG["channel"],
                "record": CONFIG["record"],
                "stream_url": CONFIG["stream_url"],
            }).encode("utf-8"))
        else:
            self.send_error(404)


def start_web_server(port):
    server = ThreadingHTTPServer(("127.0.0.1", port), WebHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Web-App: http://localhost:{port}\n")
    return server


# ------------------------------------------------------------------ Export

def export_csv():
    conn = db_connect()
    rows = conn.execute(
        "SELECT ts, channel, artist, title, raw, favorite FROM tracks ORDER BY id"
    ).fetchall()
    conn.close()
    out = BASE_DIR / "tracks.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(["Zeit", "Channel", "Artist", "Titel", "Favorit",
                         "YouTube-Suche"])
        for ts, channel, artist, title, raw, fav in rows:
            query = urllib.parse.quote_plus(f"{artist or ''} {title or raw}".strip())
            writer.writerow([
                ts, channel, artist or "", title or raw,
                "ja" if fav else "",
                f"https://www.youtube.com/results?search_query={query}",
            ])
    print(f"{len(rows)} Tracks exportiert nach: {out}")


# -------------------------------------------------------------------- Main

def main():
    parser = argparse.ArgumentParser(
        description="Protokolliert Tracks eines sunshine live Channels.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--channel", default="techno",
                        help="Channel-Slug, z.B. " + ", ".join(KNOWN_CHANNELS))
    parser.add_argument("--url", default=None,
                        help="Stream-URL direkt angeben (ueberschreibt --channel)")
    parser.add_argument("--poll", type=int, default=0, metavar="SEK",
                        help="Sparmodus: nur alle SEK Sekunden kurz verbinden "
                             "(0 = Dauerbetrieb, erfasst jeden Wechsel sofort)")
    parser.add_argument("--port", type=int, default=8765,
                        help="Port fuer die lokale Web-App")
    parser.add_argument("--no-web", action="store_true",
                        help="Web-App nicht starten")
    parser.add_argument("--export", choices=["csv"],
                        help="Nur exportieren, kein Logging")
    parser.add_argument("--record", action="store_true",
                        help="Audio mitschneiden: jeder Track wird als eigene "
                             "MP3-Datei gespeichert (recordings/<channel>/)")
    parser.add_argument("--record-dir", default=None, metavar="ORDNER",
                        help="Zielordner fuer Aufnahmen (Standard: "
                             "recordings/<channel> neben dem Programm)")
    args = parser.parse_args()

    if args.record and args.poll:
        parser.error("--record braucht den Dauerbetrieb und geht nicht "
                     "zusammen mit --poll.")

    if args.export == "csv":
        export_csv()
        return

    url = args.url or STREAM_TEMPLATE.format(channel=args.channel)
    CONFIG["channel"] = args.channel
    CONFIG["stream_url"] = url
    CONFIG["started"] = datetime.now().isoformat(timespec="seconds")
    CONFIG["record"] = args.record
    CONFIG["record_dir"] = args.record_dir
    CONFIG["poll"] = args.poll

    def handle_sigint(signum, frame):
        print("\nBeende ...")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_sigint)

    if not args.no_web:
        start_web_server(args.port)

    run_logger(poll_interval=args.poll)


if __name__ == "__main__":
    main()
