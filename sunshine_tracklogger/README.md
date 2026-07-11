# sunshine live Track-Logger

Kleines eigenständiges Programm, das mitschreibt, welche Tracks auf einem
sunshine live Channel (Standard: **Techno**) laufen — ohne dass du zuhören
musst. Solange das Programm läuft, landet jeder gespielte Track mit Uhrzeit
in einer Datenbank. Dazu gibt es eine lokale Webseite mit der Liste und
einem **YouTube-Suchlink** pro Track.

Es wird **nur Python 3 benötigt** (Standardbibliothek, nichts zu installieren).

## Starten

```
cd sunshine_tracklogger
python tracklogger.py
```

Unter Windows reicht auch ein Doppelklick auf `start_tracklogger.bat`.

Danach im Browser öffnen: **http://localhost:8765**

Dort siehst du live alle erfassten Tracks (neueste oben), kannst filtern und
per Klick direkt die YouTube-Suche zum Track öffnen. Beenden mit `Strg+C`.

## Optionen

| Befehl | Bedeutung |
|---|---|
| `python tracklogger.py` | Channel *Techno*, erfasst jeden Trackwechsel sofort |
| `python tracklogger.py --channel trance` | anderer Channel (Slug wie auf sunshine-live.de/music/channels, z. B. `techno`, `melodic-techno`, `trance`, `house`, `hardstyle`, `classics`, `live`) |
| `python tracklogger.py --poll 60` | **Sparmodus**: verbindet nur alle 60 s kurz statt dauerhaft zu streamen (weniger Datenverbrauch, kann aber sehr kurze Tracks verpassen) |
| `python tracklogger.py --export csv` | exportiert alles nach `tracks.csv` (öffnet sich in Excel, inkl. YouTube-Links) |
| `python tracklogger.py --no-web` | ohne Webseite, nur Konsole |
| `python tracklogger.py --port 9000` | anderer Port für die Webseite |

## Wie es funktioniert

Das Programm verbindet sich mit dem offiziellen Stream
(`http://stream.sunshine-live.de/techno/mp3-192/...`) und liest die
**ICY-Metadaten**, die der Sender bei jedem Trackwechsel mitschickt
(`StreamTitle='Artist - Titel'`). Die Audiodaten selbst werden verworfen.
Sender-Jingles/Eigenwerbung („sunshine live – …") werden automatisch
aussortiert. Bei Verbindungsabbrüchen verbindet es sich selbstständig neu.

Gespeichert wird in `tracks.db` (SQLite) im selben Ordner — die Liste bleibt
also auch nach einem Neustart erhalten und wächst einfach weiter.

## Hinweise

- Im Dauerbetrieb wird der Stream mitgeladen (~85 MB/Stunde bei 192 kbit/s).
  Wenn das zu viel ist: `--poll 60` nutzen (nur wenige KB pro Minute).
- Es können auch mehrere Logger parallel laufen (verschiedene Channels),
  dann aber mit unterschiedlichen Ports bzw. einmal `--no-web`.
- Nur für den privaten Gebrauch gedacht.
