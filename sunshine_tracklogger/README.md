# sunshine live Track-Logger

Kleines eigenständiges Programm, das mitschreibt, welche Tracks auf einem
sunshine live Channel (Standard: **Techno**) laufen — ohne dass du zuhören
musst. Solange das Programm läuft, landet jeder gespielte Track mit Uhrzeit
in einer Datenbank. Dazu gibt es eine lokale Web-App mit Player, Favoriten,
Statistiken und **YouTube-Suchlink** pro Track.

Es wird **nur Python 3 benötigt** (Standardbibliothek, nichts zu installieren).

## Starten

```
cd sunshine_tracklogger
python tracklogger.py
```

Unter Windows reicht auch ein Doppelklick auf `start_tracklogger.bat`.

Danach im Browser öffnen: **http://localhost:8765**

Beenden mit `Strg+C`.

## Die Web-App

- **Player**: Play-Button oben spielt den Channel direkt im Browser ab
  (mit Lautstärkeregler). Beim Fortsetzen springt er automatisch auf LIVE.
- **Channel-Wechsel**: Dropdown im Player — Logger (und Player) springen
  sofort auf den neuen Channel um, ohne Neustart des Programms.
- **REC-Schalter** (versteckt 😉): **5× schnell auf das ♫-Logo klicken**
  schaltet den Aufnahme-Button frei — nochmal 5×, und er verschwindet
  wieder. Bei aktiver Aufnahme pulsiert der Button rot und die Statuszeile
  zeigt Anzahl und Größe der bisherigen MP3s. (Läuft eine Aufnahme,
  bleibt der Button sichtbar, damit man sie immer stoppen kann.)
- **Läuft gerade**: der zuletzt erfasste Track, groß angezeigt, mit
  Direkt-Button zur YouTube-Suche.
- **Favoriten**: Stern bei einem Track anklicken, um ihn zu merken.
  Mit „★ Nur Favoriten" siehst du nur deine gemerkten Tracks —
  perfekt zum späteren Raussuchen guter Musik.
- **Trackliste**: nach Tagen gruppiert (Heute/Gestern/…), mit Suchfeld,
  Kopier-Button und YouTube-Link pro Track.
- **Statistiken**: Tracks heute/gesamt, Anzahl Interpreten, Favoriten
  sowie die Top-Artists mit Häufigkeit.
- **CSV-Button**: lädt die komplette Liste als Excel-taugliche CSV herunter
  (inkl. Favoriten-Spalte und YouTube-Links).
- Aktualisiert sich automatisch alle 10 Sekunden, auch fürs Handy-Format
  geeignet (gleiches WLAN vorausgesetzt, dann per PC-IP aufrufen —
  standardmäßig lauscht die App aber nur auf dem eigenen Rechner).

## Optionen

| Befehl | Bedeutung |
|---|---|
| `python tracklogger.py` | Channel *Techno*, erfasst jeden Trackwechsel sofort |
| `python tracklogger.py --channel trance` | anderer Channel (Slug wie auf sunshine-live.de/music/channels, z. B. `techno`, `melodic-techno`, `trance`, `house`, `hardstyle`, `classics`, `live`) |
| `python tracklogger.py --poll 60` | **Sparmodus**: verbindet nur alle 60 s kurz statt dauerhaft zu streamen (weniger Datenverbrauch, kann aber sehr kurze Tracks verpassen) |
| `python tracklogger.py --export csv` | exportiert alles nach `tracks.csv`, ohne zu loggen |
| `python tracklogger.py --no-web` | ohne Web-App, nur Konsole |
| `python tracklogger.py --port 9000` | anderer Port für die Web-App |
| `python tracklogger.py --url http://...` | Stream-URL direkt angeben, falls sich die Adresse mal ändert |
| `python tracklogger.py --record` | **Aufnahme**: jeder Track wird zusätzlich als eigene MP3 gespeichert |
| `python tracklogger.py --record --record-dir D:\Musik` | Aufnahmen in einen eigenen Ordner legen |

## Aufnahme (`--record`)

Da das Programm über die Metadaten genau weiß, wann ein Track anfängt und
endet, kann es den Stream direkt in **einzelne MP3-Dateien pro Track**
zerschneiden — fertig benannt, z. B.:

```
recordings/techno/2026-07-12 21-04 Charlotte de Witte - Doppler.mp3
```

- Tracks, bei denen Anfang oder Ende fehlt (Programmstart mitten im Track,
  Verbindungsabbruch, Beenden), bekommen den Zusatz **„(angeschnitten)"** —
  so erkennst du sofort, welche Dateien komplett sind.
- Sender-Jingles/Eigenwerbung werden nicht gespeichert.
- Platzbedarf: ca. **85 MB pro Stunde** (192 kbit/s MP3).
- Geht nur im Dauerbetrieb (nicht zusammen mit `--poll`).
- Rechtlicher Hinweis: Mitschnitte aus dem Radio sind als **Privatkopie**
  für den eigenen Gebrauch okay — nicht weiterverbreiten oder hochladen.

## Wie es funktioniert

Das Programm verbindet sich mit dem offiziellen Stream
(`http://stream.sunshine-live.de/techno/mp3-192/...`) und liest die
**ICY-Metadaten**, die der Sender bei jedem Trackwechsel mitschickt
(`StreamTitle='Artist - Titel'`). Die Audiodaten selbst werden verworfen.
Sender-Jingles/Eigenwerbung („sunshine live – …") werden automatisch
aussortiert. Bei Verbindungsabbrüchen verbindet es sich selbstständig neu.

Gespeichert wird in `tracks.db` (SQLite) im selben Ordner — die Liste
(inklusive Favoriten) bleibt also auch nach einem Neustart erhalten und
wächst einfach weiter.

## Hinweise

- Im Dauerbetrieb wird der Stream mitgeladen (~85 MB/Stunde bei 192 kbit/s).
  Wenn das zu viel ist: `--poll 60` nutzen (nur wenige KB pro Minute).
  Der eingebaute Player ist davon unabhängig und lädt nur beim Abspielen.
- Es können auch mehrere Logger parallel laufen (verschiedene Channels),
  dann aber mit unterschiedlichen Ports bzw. einmal `--no-web`.
- Nur für den privaten Gebrauch gedacht.
