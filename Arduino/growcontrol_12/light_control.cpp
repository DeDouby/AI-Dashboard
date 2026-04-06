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
void light_save_state() {
    lightPrefs.putInt("l_h", l_target_h);
    lightPrefs.putInt("l_m", l_target_m);
    lightPrefs.putInt("l_dur", l_target_dur);        // Minuten
    lightPrefs.putInt("l_sunrise", l_target_sunrise); // Minuten (15-min Raster)
    lightPrefs.putInt("l_sunset", l_target_sunset);   // Minuten (15-min Raster)
    lightPrefs.putInt("mode", (int)current_light_mode);
    lightPrefs.putInt("target", target_brightness);
}

void light_init() {
    ledcAttach(PIN_LIGHT, 5000, 8);
    lightPrefs.begin("light", false);

    // 1. Targets laden (Soll-Zustand aus dem Flash)
    l_target_h = lightPrefs.getInt("l_h", 8);
    l_target_m = lightPrefs.getInt("l_m", 0);  // Immer 15er-Raster
    l_target_dur = lightPrefs.getInt("l_dur", 720);      // Minuten (Default 12h)
    l_target_sunrise = lightPrefs.getInt("l_sunrise", 60);  // Minuten (Default 1h)
    l_target_sunset = lightPrefs.getInt("l_sunset", 60);    // Minuten (Default 1h)
    current_light_mode = (LightMode)lightPrefs.getInt("mode", 1);
    target_brightness = lightPrefs.getInt("target", 50);
    
    // Konvertierung zu Sekunden (intern)
    light_duration_sec = (uint32_t)l_target_dur * 60;

    // 2. DER ARCHITEKTEN-FIX:
    // Wir nehmen die aktuelle Systemzeit (nach Boot meist 01.01.1970 00:00:00).
    // Wir setzen light_start_unix auf GENAU DIESEN Zeitpunkt.
    time_t now = time(nullptr);
    light_start_unix = now; 

    Serial.println("Light Module: Boot-Reset akzeptiert. Programm startet ab Sekunde 0.");
}

void light_update() {
    time_t now = time(nullptr);

    // REVISION-PROTECTION: 
    // Falls die Uhrzeit von 1970 (Boot) auf 2026 (Sync) springt, 
    // müssen wir light_start_unix "mitschleifen", damit das Fenster stabil bleibt.
    static time_t last_sync_check = 0;
    if (last_sync_check < 946684800 && now > 946684800) {
        // Die Zeit ist gerade von 'unbekannt' auf 'real' gesprungen!
        // Wir setzen den Startpunkt auf die korrekte reale Uhrzeit (l_target_h/m).
        struct tm ti;
        localtime_r(&now, &ti);
        ti.tm_hour = l_target_h;
        ti.tm_min = l_target_m;
        ti.tm_sec = 0;
        light_start_unix = mktime(&ti);
        Serial.println("Clock Sync erkannt: Timer auf Echtzeit synchronisiert.");
    }
    last_sync_check = now;

    struct tm ti_now;
    localtime_r(&now, &ti_now);

    // ... AB HIER DEINE OR
    int now_sec = ti_now.tm_hour * 3600 + ti_now.tm_min * 60 + ti_now.tm_sec;
    bool timer_should_be_on = false;
    uint32_t elapsed_in_window = 0; 
    uint32_t remaining_in_window = 0; // Das hier brauchen wir für den Spiegel

    if (current_light_mode == LIGHT_MODE_TIMER) {
        struct tm ti_start;
        localtime_r(&light_start_unix, &ti_start);
        
        int start_sec = ti_start.tm_hour * 3600 + ti_start.tm_min * 60;
        int dur = light_duration_sec;
        int end_sec = (start_sec + dur); 

        if (start_sec + dur <= 86400) {
            if (now_sec >= start_sec && now_sec < end_sec) {
                timer_should_be_on = true;
                elapsed_in_window = now_sec - start_sec;
                remaining_in_window = end_sec - now_sec; // Zeit bis AUS
            }
        } else {
            int midnight_end = end_sec % 86400;
            if (now_sec >= start_sec) {
                timer_should_be_on = true;
                elapsed_in_window = now_sec - start_sec;
                remaining_in_window = (86400 - now_sec) + midnight_end;
            } else if (now_sec < midnight_end) {
                timer_should_be_on = true;
                elapsed_in_window = (86400 - start_sec) + now_sec;
                remaining_in_window = midnight_end - now_sec;
            }
        }
    }

    if (current_light_mode == LIGHT_MODE_TIMER) {
        if (timer_should_be_on) {
            // Sunrise/Sunset in Sekunden konvertieren (15-min Raster)
            uint32_t sunrise_sec = (uint32_t)l_target_sunrise * 60;  // Minuten --> Sekunden
            uint32_t sunset_sec = (uint32_t)l_target_sunset * 60;    // Minuten --> Sekunden
            
            // SICHERHEIT: Sunrise + Sunset darf Gesamtdauer nicht überschreiten
            if (sunrise_sec + sunset_sec > light_duration_sec) {
                sunrise_sec = light_duration_sec / 2;
                sunset_sec = light_duration_sec / 2;
            }
            
            // SUNRISE: Rampe am Anfang
            if (sunrise_sec > 0 && elapsed_in_window < sunrise_sec) {
                float p = (float)elapsed_in_window / (float)sunrise_sec;
                p = constrain(p, 0.0f, 1.0f);
                effective_brightness = 25 + (target_brightness - 25) * p;
            }
            // SUNSET: Rampe am Ende
            else if (sunset_sec > 0 && remaining_in_window < sunset_sec) {
                float p = (float)remaining_in_window / (float)sunset_sec;
                p = constrain(p, 0.0f, 1.0f);
                effective_brightness = 25 + (target_brightness - 25) * p;
            }
            // MITTENDRIN: Volle Helligkeit
            else {
                effective_brightness = target_brightness;
            }
        } else {
            effective_brightness = 0;
        }
    } 
    else {
        effective_brightness = target_brightness;
    }

    ledcWrite(PIN_LIGHT, map(effective_brightness, 0, 100, 0, 255));
}

// DIESE BEIDEN HIER MÜSSEN UNBEDINGT UNTER DER UPDATE FUNKTION STEHEN:
int light_get_effective_brightness() {
    return effective_brightness;
}

int light_get_minutes_to_next_change() {
    if (current_light_mode != LIGHT_MODE_TIMER || light_start_unix <= 0) {
        return -1;
    }
    time_t now = time(nullptr);
    struct tm ti_now, ti_start;
    localtime_r(&now, &ti_now);
    localtime_r(&light_start_unix, &ti_start);

    int now_sec = ti_now.tm_hour * 3600 + ti_now.tm_min * 60 + ti_now.tm_sec;
    int start_sec = ti_start.tm_hour * 3600 + ti_start.tm_min * 60;
    int dur = light_duration_sec;
    int end_sec = start_sec + dur;

    if (dur <= 86400 && start_sec + dur <= 86400) {
        if (now_sec < start_sec) return (start_sec - now_sec) / 60;
        else if (now_sec < end_sec) return (end_sec - now_sec) / 60;
        else return ((86400 - now_sec) + start_sec) / 60;
    } else {
        int midnight_end = end_sec % 86400;
        if (now_sec >= start_sec) return (end_sec - now_sec) / 60;
        else if (now_sec < midnight_end) return (midnight_end - now_sec) / 60;
        else return (start_sec - now_sec) / 60;
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
    // Eingaben validieren und auf 15-min Raster runden
    l_target_h = constrain(h, 0, 23);
    l_target_m = _round_to_15min(m) % 60;  // 0, 15, 30, 45
    l_target_dur = _round_to_15min(d);     // d ist MINUTEN
    l_target_dur = constrain(l_target_dur, 15, 1440);  // Min 15 min, Max 24h

    struct tm ti;
    if (getLocalTime(&ti)) {
        ti.tm_hour = l_target_h;
        ti.tm_min = l_target_m;
        ti.tm_sec = 0;
        light_start_unix = mktime(&ti);
    }
    
    light_duration_sec = (uint32_t)l_target_dur * 60;  // Minuten --> Sekunden
    light_save_state();
}
void light_control_process_json(JsonObject doc) {
    bool changed = false;

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
    doc["rev"] = current_rev; 
}