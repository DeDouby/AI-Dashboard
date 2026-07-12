# sunshine live Track-Logger 🎧

Protokolliert, welche Tracks auf einem [sunshine live](https://www.sunshine-live.de)
Channel (Standard: **Techno**) laufen — ohne dass du zuhören musst. Solange das
Programm läuft, landet jeder gespielte Track mit Uhrzeit in einer Datenbank.
Dazu gibt es eine lokale Web-App mit Player, Favoriten, Aufnahme-Funktion und
YouTube-Suchlink pro Track.

## Schnellstart (Windows, ohne Installation)

1. Oben rechts auf **Code → Download ZIP** klicken und entpacken
   (oder das Repo klonen)
2. Doppelklick auf **`start_tracklogger.bat`**
3. Fertig — der Browser öffnet sich automatisch mit der Track-Liste

Ist kein Python auf dem Rechner, lädt die BAT beim ersten Start einmalig ein
**portables Python** (~11 MB, offiziell von python.org) in den Unterordner
`python-embed\` — es wird nichts installiert, nichts verändert, und der ganze
Ordner bleibt einfach löschbar/verschiebbar.

Auf Linux/Mac: `python3 tracklogger.py --open`

## Die Web-App

- **Player**: Play-Button spielt den Channel direkt im Browser ab
  (Lautstärkeregler inklusive). Beim Fortsetzen springt er auf LIVE.
- **Channel-Wechsel**: Dropdown mit über 25 Channels — Logger und Player
  springen sofort um. Fehlt einer: unten **„✎ eigener Channel …"** wählen
  und den Namen aus der Stream-URL eintippen. Bei falschem Namen zeigt
  die Statuszeile ein ⚠ mit dem Fehler.
- **Spieldauer**: sobald der nächste Track startet, steht beim vorherigen,
  wie lange er lief.
- **Favoriten**: Stern anklicken zum Merken, Filter „★ Nur Favoriten" —
  perfekt zum späteren Raussuchen guter Musik.
- **⟲ Nachladen**: holt über die offizielle sunshine live Playlist-API nach,
  was auf dem Channel lief, auch wenn der Logger aus war. Ohne Datum: die
  letzten 24 h. Mit **Datum/Uhrzeit** im Feld daneben: ±3 h um den Zeitpunkt
  („was lief da eigentlich Samstagnacht?"). Beim allerersten Klick pro
  Channel sucht sich das Programm die passende Station selbst (~1 Minute),
  danach geht es sofort.
- **Aufnahme** (versteckt 😉): **5× schnell auf das ♫-Logo klicken** schaltet
  den REC-Button frei — nochmal 5×, und er verschwindet wieder. Bei aktiver
  Aufnahme pulsiert er rot. Gespeicherte Tracks bekommen in der Liste ein
  gelbes Download-Symbol (Tooltip zeigt den Dateinamen).
- **CSV-Export**, Suchfeld, Kopier-Button und YouTube-Link pro Track.
- Aktualisiert sich alle 10 Sekunden von selbst.

## Aufnahme (`--record` bzw. REC-Button)

Da das Programm über die Stream-Metadaten weiß, wann ein Track anfängt und
endet, zerschneidet es den Stream direkt in **einzelne MP3s pro Track**:

```
recordings/techno/Charlotte de Witte - Doppler.mp3
```

- Tracks mit fehlendem Anfang/Ende (Programmstart mitten im Track,
  Verbindungsabbruch, Beenden) bekommen den Zusatz **„(angeschnitten)"**.
- Jingles/Senderwerbung werden nicht gespeichert.
- Platzbedarf: ca. 85 MB pro Stunde (192-kbit/s-MP3).
- Rechtlich: Radio-Mitschnitte sind als **Privatkopie** für den eigenen
  Gebrauch okay — nicht weiterverbreiten oder hochladen.

## Optionen (Kommandozeile)

| Befehl | Bedeutung |
|---|---|
| `python tracklogger.py` | Channel *Techno*, Web-App auf Port 8765 |
| `... --channel trance` | anderer Channel (Slug wie auf sunshine-live.de/music/channels) |
| `... --open` | Browser automatisch öffnen (macht die BAT von selbst) |
| `... --record` | Aufnahme direkt ab Start aktivieren |
| `... --record-dir D:\Musik` | eigener Zielordner für MP3s |
| `... --poll 60` | Sparmodus: nur alle 60 s kurz verbinden statt Dauerstream |
| `... --export csv` | alles nach `tracks.csv` exportieren, ohne zu loggen |
| `... --port 9000` | anderer Port für die Web-App |
| `... --no-web` | nur Konsole, keine Web-App |
| `... --url http://...` | Stream-URL direkt angeben, falls sie sich mal ändert |

## Wie es funktioniert

Das Programm verbindet sich mit dem offiziellen Stream
(`http://stream.sunshine-live.de/<channel>/mp3-192/...`) und liest die
**ICY-Metadaten**, die der Sender bei jedem Trackwechsel mitschickt
(`StreamTitle='Artist - Titel'`). Ohne Aufnahme werden die Audiodaten
verworfen. Jingles werden gefiltert, bei Abbrüchen verbindet es sich selbst
neu. Gespeichert wird in `tracks.db` (SQLite) im Programmordner — alles
bleibt über Neustarts erhalten.

Benötigt nur die **Python-Standardbibliothek** (Python 3.8+) — keine
Abhängigkeiten, keine API-Keys, keine Kosten.

## Hinweise

- Im Dauerbetrieb wird der Stream mitgeladen (~85 MB/Stunde). Wenn das zu
  viel ist: `--poll 60` (wenige KB/Minute, kann sehr kurze Tracks verpassen —
  Aufnahme geht damit nicht).
- Mehrere Logger parallel (verschiedene Channels) gehen, dann verschiedene
  Ports bzw. `--no-web` nutzen.
- Die angezeigte Spieldauer ist die Zeit zwischen zwei Trackwechseln im
  Stream — bei gemixten Übergängen also ein „ca."-Wert.
- Privates Hobby-Projekt, nicht mit sunshine live/Regiocast verbunden.
