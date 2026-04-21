#include "web_server_browser.h"
#include "light_control.h"
#include <time.h>

extern const char* www_username;
extern const char* www_password;

static void handleSetLight(WebServer& server) {
    if (!server.authenticate(www_username, www_password)) return server.requestAuthentication();
    
    // 1. Timer-Settings
    if (server.hasArg("th") && server.hasArg("tm") && server.hasArg("td")) {
        light_set_timer(server.arg("th").toInt(), server.arg("tm").toInt(), server.arg("td").toInt());
    }

    // 2. Modus & Slider-Logik (KORRIGIERT)
    if (server.hasArg("lmode")) {
        String m = server.arg("lmode");
        if (m == "stop") {
            light_set_mode(LIGHT_MODE_MANUAL);
            light_set_brightness(0); // Hier wird AUS geschaltet
        } else if (m == "tim") {
            light_set_mode(LIGHT_MODE_TIMER);
        } else {
            light_set_mode(LIGHT_MODE_MANUAL);
        }
    } 
    // ZIEL: Slider nur verarbeiten, wenn NICHT gerade "stop" gedrückt wurde
    else if (server.hasArg("brightness")) {
        light_set_brightness(server.arg("brightness").toInt());
    }

    server.sendHeader("Location", "/"); 
    server.send(303);
}

static void handleRoot(WebServer& server) {
    if (!server.authenticate(www_username, www_password)) return server.requestAuthentication();
    
    // UHRZEIT VOM ESP HOLEN
    struct tm ti;
    char timeStr[16];
    if (getLocalTime(&ti)) {
        sprintf(timeStr, "%02d:%02d:%02d", ti.tm_hour, ti.tm_min, ti.tm_sec);
    } else {
        strcpy(timeStr, "ZEIT NICHT SYNCHRON");
    }

    int br = light_get_effective_brightness();
    int rem = light_get_minutes_to_next_change();

    String html = "<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>";
    // Auto-Refresh alle 30 Sekunden
    html += "<meta http-equiv='refresh' content='30'>";
    html += "<style>body{font-family:sans-serif;text-align:center;background:#111;color:#eee;} .card{background:#222;padding:20px;margin:10px;border-radius:15px;border:1px solid #444;} .val{color:#0f0;font-size:2.5em;font-weight:bold;} .time-display{font-size:1.5em; color:#ffcc00; margin-bottom:10px;} .slider{width:100%;height:50px;} .btn{padding:15px;background:#444;color:white;text-decoration:none;display:inline-block;margin:5px;border-radius:10px;font-weight:bold; min-width:90px;}</style></head><body>";
    
    html += "<h1>GROW-SYNC MASTER</h1>";
    
    // DIE UHRZEIT-CARD
    html += "<div class='card'>";
    html += "<div class='time-display'>ESP-ZEIT: " + String(timeStr) + "</div>";
    html += "<p style='color:#aaa;'>Prüfe, ob diese Zeit mit deiner echten Uhrzeit übereinstimmt.</p>";
    html += "</div>";

    // LICHT-STATUS
    html += "<div class='card'><h2>Licht-Leistung: <span class='val'>" + String(br) + "%</span></h2>";
    if(current_light_mode == LIGHT_MODE_TIMER) {
        html += "<p style='color:#00b3ff;'>Timer aktiv - Wechsel in: " + String(rem) + " Min.</p>";
    }
    
    html += "<form action='/set_light' method='get'>";
    int sMin = 25; // Hard-Limit für den Slider
    html += "<input type='range' name='brightness' min='25' max='100' value='"+String(br < 25 ? 25 : br)+"' class='slider' onchange='this.form.submit()'>";    
    html += "<br><br><a href='/set_light?lmode=man' class='btn'>MANUELL</a>";
    html += "<a href='/set_light?lmode=tim' class='btn' style='background:#0088cc;'>TIMER</a>";
    html += "<a href='/set_light?lmode=stop' class='btn' style='background:#900;'>OFF (0%)</a>";
    html += "</form></div>";

    // TIMER EINSTELLUNGEN
    html += "<div class='card'><h3>Timer-Konfiguration</h3><form action='/set_light' method='get'>";
    html += "Start (HH:MM): <input type='number' name='th' style='width:50px' min='0' max='23'> : <input type='number' name='tm' style='width:50px' min='0' max='59'><br><br>";
    html += "Dauer (in Stunden): <input type='number' name='td' style='width:60px' min='1' max='24'><br><br>";
    html += "<input type='submit' value='TIMER SPEICHERN' style='padding:10px; background:#28a745; color:white; border:none; border-radius:5px;'>";
    html += "</form></div>";

    html += "</body></html>";
    server.send(200, "text/html", html);
}

namespace WebServerBrowser {
    void registerRoutes(WebServer& server) {
        server.on("/", [&server]() { handleRoot(server); });
        server.on("/set_light", [&server]() { handleSetLight(server); });
    }
}