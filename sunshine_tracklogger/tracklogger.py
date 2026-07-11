#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sunshine live Track-Logger
==========================
Lauscht am sunshine live Stream (Standard: Channel "Techno") und protokolliert
alle gespielten Tracks in eine SQLite-Datenbank. Solange das Programm laeuft,
werden die Titel gesammelt - man muss den Stream nicht anhoeren.

Zusaetzlich gibt es eine kleine lokale Webseite (http://localhost:8765) mit
der Live-Trackliste inkl. YouTube-Suchlink pro Track.

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
from datetime import datetime
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


def iter_stream_titles(url, single_shot=False):
    """Generator: liefert jeden StreamTitle, sobald er sich im Stream aendert.
    Bei single_shot=True wird nur der erste gefundene Titel geliefert."""
    f, sock, metaint = open_icy_stream(url)
    try:
        while not stop_event.is_set():
            read_exact(f, metaint)  # Audiodaten verwerfen
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


def run_logger(channel, url, poll_interval=0):
    conn = db_connect()
    backoff = 2
    print(f"Logge Channel '{channel}'  ->  {url}")
    print(f"Datenbank: {DB_PATH}")
    if poll_interval:
        print(f"Sparmodus: alle {poll_interval}s wird kurz nachgeschaut.\n")
    else:
        print("Dauerbetrieb: jeder Trackwechsel wird sofort erfasst.\n")

    last_seen = None
    while not stop_event.is_set():
        try:
            if poll_interval:
                for raw in iter_stream_titles(url, single_shot=True):
                    if raw != last_seen:
                        log_title(conn, channel, raw)
                        last_seen = raw
                backoff = 2
                stop_event.wait(poll_interval)
            else:
                for raw in iter_stream_titles(url):
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
    conn.close()
    print("Logger beendet.")


# ------------------------------------------------------------------ Web-UI

PAGE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>sunshine live Track-Logger</title>
<style>
  :root { color-scheme: dark; }
  body { font-family: system-ui, sans-serif; background:#111418; color:#e8eaed;
         margin:0; padding:1.2rem; }
  h1 { font-size:1.15rem; margin:0 0 .2rem; }
  .sub { color:#9aa0a6; font-size:.85rem; margin-bottom:1rem; }
  input { width:100%; max-width:26rem; padding:.5rem .7rem; border-radius:.5rem;
          border:1px solid #3c4043; background:#1b1f24; color:inherit;
          font-size:.95rem; margin-bottom:1rem; }
  table { border-collapse:collapse; width:100%; }
  th, td { text-align:left; padding:.45rem .6rem; border-bottom:1px solid #2a2e33;
           font-size:.92rem; vertical-align:top; }
  th { color:#9aa0a6; font-weight:600; position:sticky; top:0; background:#111418; }
  td.time { white-space:nowrap; color:#9aa0a6; }
  a { color:#8ab4f8; text-decoration:none; }
  a:hover { text-decoration:underline; }
  .yt { white-space:nowrap; }
</style></head><body>
<h1>sunshine live Track-Logger</h1>
<div class="sub" id="status">lade ...</div>
<input id="filter" placeholder="Filtern (Artist oder Titel) ..." oninput="render()">
<table><thead><tr><th>Zeit</th><th>Channel</th><th>Track</th><th></th></tr></thead>
<tbody id="rows"></tbody></table>
<script>
let tracks = [];
function ytLink(t) {
  const q = encodeURIComponent(((t.artist ? t.artist + " " : "") + t.title).trim());
  return "https://www.youtube.com/results?search_query=" + q;
}
function esc(s) { const d = document.createElement("div"); d.textContent = s || ""; return d.innerHTML; }
function render() {
  const f = document.getElementById("filter").value.toLowerCase();
  const rows = tracks
    .filter(t => !f || (t.raw || "").toLowerCase().includes(f))
    .map(t => `<tr><td class="time">${esc(t.ts)}</td><td>${esc(t.channel)}</td>` +
              `<td>${esc(t.raw)}</td>` +
              `<td class="yt"><a href="${ytLink(t)}" target="_blank" rel="noopener">&#9654; YouTube</a></td></tr>`)
    .join("");
  document.getElementById("rows").innerHTML = rows;
}
async function load() {
  try {
    const r = await fetch("/api/tracks?limit=500");
    tracks = await r.json();
    document.getElementById("status").textContent =
      tracks.length + " Tracks erfasst - aktualisiert " + new Date().toLocaleTimeString();
    render();
  } catch (e) {
    document.getElementById("status").textContent = "Keine Verbindung zum Logger.";
  }
}
load();
setInterval(load, 10000);
</script></body></html>"""


class WebHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # keine Request-Logs in der Konsole

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == "/api/tracks":
            qs = urllib.parse.parse_qs(parsed.query)
            try:
                limit = min(int(qs.get("limit", ["200"])[0]), 5000)
            except ValueError:
                limit = 200
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute(
                "SELECT ts, channel, artist, title, raw FROM tracks "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            conn.close()
            data = [
                {"ts": r[0], "channel": r[1], "artist": r[2],
                 "title": r[3], "raw": r[4]}
                for r in rows
            ]
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)


def start_web_server(port):
    server = ThreadingHTTPServer(("127.0.0.1", port), WebHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Web-Ansicht: http://localhost:{port}\n")
    return server


# ------------------------------------------------------------------ Export

def export_csv():
    conn = db_connect()
    rows = conn.execute(
        "SELECT ts, channel, artist, title, raw FROM tracks ORDER BY id"
    ).fetchall()
    conn.close()
    out = BASE_DIR / "tracks.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(["Zeit", "Channel", "Artist", "Titel", "Roh", "YouTube-Suche"])
        for ts, channel, artist, title, raw in rows:
            query = urllib.parse.quote_plus(f"{artist or ''} {title or raw}".strip())
            writer.writerow([
                ts, channel, artist or "", title or "", raw,
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
                        help="Port fuer die lokale Web-Ansicht")
    parser.add_argument("--no-web", action="store_true",
                        help="Web-Ansicht nicht starten")
    parser.add_argument("--export", choices=["csv"],
                        help="Nur exportieren, kein Logging")
    args = parser.parse_args()

    if args.export == "csv":
        export_csv()
        return

    url = args.url or STREAM_TEMPLATE.format(channel=args.channel)

    def handle_sigint(signum, frame):
        print("\nBeende ...")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_sigint)

    if not args.no_web:
        start_web_server(args.port)

    run_logger(args.channel, url, poll_interval=args.poll)


if __name__ == "__main__":
    main()
