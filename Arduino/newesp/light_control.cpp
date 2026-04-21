///////////////////////////////////////////////////////////////////////////////
// !!! ABSOLUTES GESETZ: DAS TARGET-REVISION-PRINZIP (C++ / ESP32) !!!
// -------------------------------------------------------------------------
// 1. HARDWARE FOLGT TARGET: Die Loop darf NIEMALS direkt auf UI-Inputs reagieren.
//    Sie vergleicht permanent: 'target_val' vs 'effective_val'.
//
// 2. REVISION-CONFIRMATION: Der ESP32 bestätigt eine Änderung NUR, indem er 
//    die empfangene 'rev' (Revision) im Status-Paket unverändert zurücksendet.
//
// 3. KEINE LÜGEN: Der Status 'Synced' (Grün in der App) darf NUR dann entstehen,
//    wenn 'esp32_rev' == 'ui_target_rev'.
//
// 4. ATOMARE UPDATES: Bei Empfang eines neuen Targets wird die 'rev' sofort 
//    gespeichert, aber der 'effective_val' zieht (ggf. über Rampen) stur nach.
//
// JEDE KI-ÄNDERUNG MUSS DIESE ASYNCHRONE LOGIK WAHREN. DIREKTES ÜBERSCHREIBEN
// VON PINS OHNE TARGET-ABGLEICH IST EIN SYSTEMFEHLER!
///////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////
// !!! ERWEITERUNG: ZEITKONSISTENZ-PRINZIP (RTC / NTP / REBOOT) !!!
// -------------------------------------------------------------------------
// 5. ZEIT IST EINE KONTINUIERLICHE ACHSE:
//    Zeit wird als fortlaufend betrachtet – unabhängig von Reboots,
//    Internetverbindung oder Synchronisationsereignissen.
//
// 6. KEINE VERGANGENHEIT, KEIN RESET:
//    Timer-Startpunkte (z. B. light_start_unix) werden NIEMALS relativ zum
//    Boot interpretiert, sondern immer absolut zur aktuellen Uhrzeit.
//
//    Ein Reboot darf NIEMALS dazu führen, dass:
//    - Timer neu bei 0 starten
//    - vergangene Zeit ignoriert wird
//    - ein künstlicher Startpunkt erzeugt wird
//
// 7. VERGANGENE TIMER SIND REAL:
//    Liegt der aktuelle Zeitpunkt innerhalb eines bereits gestarteten
//    Timerfensters (auch wenn der Start vor dem Boot lag),
//    MUSS das System sofort den korrekten Zustand berechnen:
//
//    → elapsed_in_window = now - start
//    → Zustand ergibt sich deterministisch aus aktueller Zeit
//
//    Es gibt KEIN „Nachholen“, KEIN „Neustart“, KEIN „Reset“.
//
// 8. ZEITQUELLE IST AUSTAUSCHBAR, LOGIK NICHT:
//    Die Quelle der Zeit (RTC wie DS3231 RTC Module,
//    NTP oder Systemzeit) ist austauschbar,
//    ABER die Timer-Logik basiert IMMER auf absoluter Zeit.
//
// 9. SYNCHRONISATION IST EIN SPRUNG, KEIN NEUSTART:
//    Wenn sich die Zeitquelle ändert (z. B. von RTC → NTP),
//    darf KEIN Timer neu initialisiert werden.
//
//    Stattdessen gilt:
//    → Der neue Zeitwert ersetzt sofort 'now'
//    → Alle Zustände werden daraus NEU BERECHNET
//
//    Es erfolgt KEINE Anpassung von:
//    - light_start_unix
//    - Timer-Dauer
//
// 10. SYSTEM IST JEDERZEIT REKONSTRUIERBAR:
//     Der komplette Zustand (AN/AUS, Rampenphase, Restzeit)
//     muss ausschließlich aus folgenden Werten bestimmbar sein:
//
//     - aktuelle Zeit (now)
//     - gespeicherte Targets (Startzeit, Dauer, Parameter)
//
//     → Keine versteckten Zustände
//     → Keine Abhängigkeit von Laufzeit-Historie
//
// JEDE KI-ÄNDERUNG MUSS DIESES ZEITMODELL EINHALTEN.
// EIN TIMER, DER VOM BOOT ABHÄNGT, IST EIN SYSTEMFEHLER.
///////////////////////////////////////////////////////////////////////////////
#include "light_control.h"
#include <time.h>
#include <Preferences.h>
#include "config.h"      // <--- WICHTIG: Hier kommt PIN_LIGHT her
Preferences lightPrefs;

time_t light_start_unix = 0;
uint32_t light_duration_sec = 43200;  // Sekunden
int target_brightness = 50;
int effective_brightness = 0;
// ===== 15-MINUTEN-RASTER (ab jetzt) =====
int l_target_h = 8;         // Stunden (0-23)
int l_target_m = 0;         // Minuten (0, 15, 30, 45 ONLY)
int l_target_dur = 720;     // MINUTEN (nicht Stunden!) --> 720 min = 12h
int l_target_sunrise = 60;  // MINUTEN (15er-Raster)
int l_target_sunset = 60;   // MINUTEN (15er-Raster)
LightMode current_light_mode = LIGHT_MODE_MANUAL;
// ... deine anderen Variablen ...
extern uint32_t current_rev;
static uint32_t light_rev = 0;              // ← NEU: Eigenes Revision für das Licht-Modul
static uint32_t light_init_rev = 0;
void light_reconstruct_after_boot();

void light_save_state() {
    lightPrefs.putInt("l_h", l_target_h);
    lightPrefs.putInt("l_m", l_target_m);
    lightPrefs.putInt("l_dur", l_target_dur);        // Minuten
    lightPrefs.putInt("l_sunrise", l_target_sunrise); // Minuten (15-min Raster)
    lightPrefs.putInt("l_sunset", l_target_sunset);   // Minuten (15-min Raster)
    lightPrefs.putInt("mode", (int)current_light_mode);
    lightPrefs.putInt("target", target_brightness);
}

// === REBOOT RECONSTRUCT ===
void light_reconstruct_after_boot() {
    if (current_light_mode == LIGHT_MODE_TIMER) {
        // rebuild start time deterministically
        struct tm ti;
        time_t now = time(nullptr);

        if (now > 946684800) {
            localtime_r(&now, &ti);
            ti.tm_hour = l_target_h;
            ti.tm_min = l_target_m;
            ti.tm_sec = 0;
            light_start_unix = mktime(&ti);
        }
    }
}

void light_init() {
    ledcAttach(PIN_LIGHT, 5000, 8);
    lightPrefs.begin("light", false);

    // Targets laden
    l_target_h = lightPrefs.getInt("l_h", 8);
    l_target_m = lightPrefs.getInt("l_m", 0);
    l_target_dur = lightPrefs.getInt("l_dur", 720);
    l_target_sunrise = lightPrefs.getInt("l_sunrise", 60);
    l_target_sunset = lightPrefs.getInt("l_sunset", 60);
    current_light_mode = (LightMode)lightPrefs.getInt("mode", (int)LIGHT_MODE_MANUAL);
    target_brightness = lightPrefs.getInt("target", 50);

    light_duration_sec = (uint32_t)l_target_dur * 60;
    light_reconstruct_after_boot();
    // === NEU: Kein Boot-Reset mehr! ===
    // Wenn wir schon eine gültige Zeit haben → light_start_unix korrekt setzen
    time_t now = time(nullptr);
    if (now > 946684800) { // > Jahr 2000
        struct tm ti;
        localtime_r(&now, &ti);
        ti.tm_hour = l_target_h;
        ti.tm_min = l_target_m;
        ti.tm_sec = 0;
        light_start_unix = mktime(&ti);
        Serial.println("Light: Startzeit aus aktueller Uhrzeit berechnet");
    } else {
        light_start_unix = 0; // noch keine gültige Zeit
    }
    light_update();
    Serial.println("Light Module initialisiert (stabiler Modus)");
}

void light_update() {
    time_t now = time(nullptr);
    if (now < 1000000) return; // Ohne Zeit kein Licht-Timer

    struct tm ti_now;
    localtime_r(&now, &ti_now);
    int now_sec = ti_now.tm_hour * 3600 + ti_now.tm_min * 60 + ti_now.tm_sec;
    
    bool timer_should_be_on = false;
    uint32_t elapsed = 0; 
    uint32_t remaining = 0;

    if (current_light_mode == LIGHT_MODE_TIMER) {
        int start_sec = l_target_h * 3600 + l_target_m * 60;
        int dur_sec = l_target_dur * 60;
        int end_sec = start_sec + dur_sec;

        // Logik für Tag & Nachtübersprung
        if (end_sec <= 86400) {
            if (now_sec >= start_sec && now_sec < end_sec) {
                timer_should_be_on = true;
                elapsed = now_sec - start_sec;
                remaining = end_sec - now_sec;
            }
        } else {
            int overflow = end_sec - 86400;
            if (now_sec >= start_sec || now_sec < overflow) {
                timer_should_be_on = true;
                elapsed = (now_sec >= start_sec) ? (now_sec - start_sec) : (86400 - start_sec + now_sec);
                remaining = (now_sec >= start_sec) ? (86400 - now_sec + overflow) : (overflow - now_sec);
            }
        }

        if (timer_should_be_on) {
            uint32_t sunrise_sec = l_target_sunrise * 60;
            uint32_t sunset_sec = l_target_sunset * 60;
            
            // Rampen-Berechnung
            if (elapsed < sunrise_sec) {
                effective_brightness = (target_brightness * elapsed) / sunrise_sec;
            } else if (remaining < sunset_sec) {
                effective_brightness = (target_brightness * remaining) / sunset_sec;
            } else {
                effective_brightness = target_brightness;
            }
        } else {
            effective_brightness = 0;
        }
    } else {
        effective_brightness = target_brightness; // Manueller Modus
    }

    ledcWrite(PIN_LIGHT, map(effective_brightness, 0, 100, 0, 255));
}

// DIESE BEIDEN HIER MÜSSEN UNBEDINGT UNTER DER UPDATE FUNKTION STEHEN:
int light_get_effective_brightness() {
    return effective_brightness;
}

int light_get_minutes_to_next_change() {
    time_t now = time(nullptr);
    if (now < 946684800) return -1; // Noch kein gültiger Zeit-Sync

    struct tm ti_now;
    localtime_r(&now, &ti_now);
    
    // Aktuelle Sekunden seit Mitternacht
    int now_sec = ti_now.tm_hour * 3600 + ti_now.tm_min * 60 + ti_now.tm_sec;
    
    // Timer-Daten
    int start_sec = l_target_h * 3600 + l_target_m * 60;
    int dur_sec = l_target_dur * 60;
    int end_sec = start_sec + dur_sec;

    // Modus Check
    if (current_light_mode != LIGHT_MODE_TIMER) return -1;

    // Fall A: Timer läuft innerhalb eines Tages (z.B. 08:00 - 20:00)
    if (end_sec <= 86400) {
        if (now_sec < start_sec) {
            // Licht noch aus -> Zeit bis AN
            return (start_sec - now_sec) / 60;
        } else if (now_sec < end_sec) {
            // Licht an -> Zeit bis AUS
            return (end_sec - now_sec) / 60;
        } else {
            // Licht bereits aus für heute -> Zeit bis morgen Start
            return (86400 - now_sec + start_sec) / 60;
        }
    } 
    // Fall B: Timer geht über Mitternacht (z.B. 20:00 - 04:00)
    else {
        int overflow_end_sec = end_sec - 86400;
        if (now_sec >= start_sec) {
            // Wir sind im ersten Teil der Nacht (vor Mitternacht) -> Zeit bis AUS
            return (end_sec - now_sec) / 60;
        } else if (now_sec < overflow_end_sec) {
            // Wir sind im zweiten Teil der Nacht (nach Mitternacht) -> Zeit bis AUS
            return (overflow_end_sec - now_sec) / 60;
        } else {
            // Wir sind im "Tag-Loch" (Licht aus) -> Zeit bis Start am Abend
            return (start_sec - now_sec) / 60;
        }
    }
}

void light_set_brightness(int p) {
    // Wir setzen nur den Zielwert. 
    // Der Modus (Timer oder Manuell) bleibt einfach so, wie er ist!
    target_brightness = constrain(p, 0, 100);
    
    // Preferences speichern, damit der Wert nach Reboot bleibt
    light_save_state();
    
    // Sofortiges Update der PWM-Ausgabe
    light_update();
}

void light_set_mode(LightMode m) {
    // Wir setzen den neuen Modus
    current_light_mode = m;
    
    // HINWEIS: Wir löschen light_start_unix NICHT auf 0.
    // Warum? Damit der User von MANUELL zurück auf TIMER schalten kann,
    // ohne die Uhrzeit im Overlay neu eintippen zu müssen.
    
    // Falls wir in einen Effekt-Modus gehen (Breath/Flicker), 
    // sorgt light_update() später für die richtige Berechnung.
    
    light_save_state();
    light_update();
}

// 15-Minuten-Raster Validierung
int _round_to_15min(int minutes) {
    return ((minutes + 7) / 15) * 15;  // Rundet auf nächstes 15er-Vielfaches
}

// light_set_timer() - d = Minuten (nicht Stunden!)
void light_set_timer(int h, int m, int d) {
    l_target_h = constrain(h, 0, 23);
    l_target_m = _round_to_15min(m) % 60;
    l_target_dur = constrain(_round_to_15min(d), 15, 1440);
    light_duration_sec = (uint32_t)l_target_dur * 60;

    // Widget-Rettung: Wir bauen einen validen Timestamp für HEUTE
    time_t now = time(nullptr);
    struct tm ti;
    if (now > 1000000) {
        localtime_r(&now, &ti);
    } else {
        // Fallback falls Zeit noch auf 1970 steht
        ti.tm_year = 126; // 2026
        ti.tm_mon = 3;
        ti.tm_mday = 17;
    }
    ti.tm_hour = l_target_h;
    ti.tm_min = l_target_m;
    ti.tm_sec = 0;
    
    light_start_unix = mktime(&ti); 
    
    light_save_state();
    Serial.printf("RECOVERY: Timer auf %02d:%02d gesetzt.\n", l_target_h, l_target_m);
}

void light_control_process_json(JsonObject doc) {
    bool changed = false;
    uint32_t received_rev = 0;
    if (doc.containsKey("rev_light")) {
        received_rev = doc["rev_light"];
    }

    // Nur verarbeiten wenn die Revision neu ist
    if (received_rev > light_rev) {

        light_rev = received_rev;
    } else {
        // Revision ist alt oder gleich, also ignorieren
        Serial.printf("Light Control: Ignoring old revision %u (current: %u)\n", received_rev, light_rev);
        return;
    }

    // 1. Not-Aus / Stop
    if (doc.containsKey("light_stop") && (int)doc["light_stop"] == 1) {
        light_set_mode(LIGHT_MODE_MANUAL);
        light_set_brightness(0);
        return; // Sofort raus hier
    }

    // 2. Timer-Einstellungen (Startzeit, Dauer, Sunrise/Sunset Rampen)
    if (doc.containsKey("l_start_h") || doc.containsKey("l_dur") || doc.containsKey("l_sunrise") || doc.containsKey("l_sunset")) {
    
        int h = doc.containsKey("l_start_h") ? (int)doc["l_start_h"] : l_target_h;
        int m = doc.containsKey("l_start_m") ? (int)doc["l_start_m"] : l_target_m;
        int d = doc.containsKey("l_dur") ? (int)doc["l_dur"] : l_target_dur;  // d = Minuten
        
        // Sunrise/Sunset Rampen (in Minuten, 15er-Raster)
        if (doc.containsKey("l_sunrise")) {
            l_target_sunrise = _round_to_15min((int)doc["l_sunrise"]);
            l_target_sunrise = constrain(l_target_sunrise, 0, d);
        }
        if (doc.containsKey("l_sunset")) {
            l_target_sunset = _round_to_15min((int)doc["l_sunset"]);
            l_target_sunset = constrain(l_target_sunset, 0, d);
        }
    
        light_set_timer(h, m, d);
        changed = true;
    }

    // 3. Helligkeit (Slider)
    if (doc.containsKey("light_pct")) {
        light_set_brightness((int)doc["light_pct"]);
        changed = true;
    }

    // 4. Modus-Wechsel
    if (doc.containsKey("light_mode")) {
        String lm = doc["light_mode"];
        if (lm == "tim") light_set_mode(LIGHT_MODE_TIMER);
        else if (lm == "man") light_set_mode(LIGHT_MODE_MANUAL);
        else if (lm == "brth") light_set_mode(LIGHT_MODE_BREATH);
        else if (lm == "flicker") light_set_mode(LIGHT_MODE_FLICKER);
        changed = true;
    }

    if (changed) {
        light_save_state();
        Serial.println("Light Settings updated via JSON.");
    }
}
void light_control_get_status(JsonObject doc) {
    doc["light_pct"] = light_get_effective_brightness();
    doc["light_target"] = target_brightness; 

    // Targets für UI (15-min Raster)
    doc["l_start_h"] = l_target_h;
    doc["l_start_m"] = l_target_m;
    doc["l_dur"] = l_target_dur;          // MINUTEN (nicht Stunden)
    doc["l_sunrise"] = l_target_sunrise;  // MINUTEN (15-min Raster)
    doc["l_sunset"] = l_target_sunset;    // MINUTEN (15-min Raster)
    
    doc["light_mode"] = (current_light_mode == LIGHT_MODE_TIMER) ? "tim" : "man";
    doc["light_remaining"] = light_get_minutes_to_next_change();
    doc["rev_light"] = light_rev;
    doc["rev_init_light"] = light_init_rev;
}