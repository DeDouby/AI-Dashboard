#include "web_server_browser.h"
#include "light_control.h"
#include <WebServer.h>
#include <ArduinoJson.h>

extern WebServer server;
extern const char* www_username;
extern const char* www_password;

void handleData();
void handleControlJSON();

const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GROW-SYNC MASTER</title>
    <style>
        :root {
            --bg-main: #111116;
            --bg-card: #1c1c24;
            --bg-input: #2a2a35;
            --border: #2d2d3d;
            --text-main: #eeeef5;
            --text-muted: #8a8a9e;
            --accent-green: #2ecc71;
            --accent-blue: #3498db;
            --accent-orange: #e67e22;
            --accent-red: #e74c3c;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg-main);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .container {
            width: 100%;
            max-width: 900px;
        }
        h1 {
            text-align: center;
            font-size: 1.8rem;
            letter-spacing: 2px;
            color: var(--text-main);
            margin-bottom: 20px;
            border-bottom: 2px solid var(--border);
            padding-bottom: 10px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }
        .card h2 {
            margin-top: 0;
            font-size: 1.2rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 8px;
            color: var(--text-main);
        }
        .status-val {
            font-size: 2rem;
            font-weight: bold;
            color: var(--accent-green);
            margin: 10px 0;
        }
        .sub-text {
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 15px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 5px;
        }
        .row {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        input[type="number"], select {
            background: var(--bg-input);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 8px;
            border-radius: 6px;
            width: 100%;
            box-sizing: border-box;
        }
        input[type="range"] {
            width: 100%;
            margin: 15px 0;
        }
        .btn {
            background: var(--bg-input);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 10px 15px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.2s;
            text-align: center;
        }
        .btn:hover { background: var(--border); }
        .btn-primary { background: var(--accent-blue); border-color: var(--accent-blue); }
        .btn-primary:hover { background: #2980b9; }
        .btn-danger { background: var(--accent-red); border-color: var(--accent-red); }
        .btn-danger:hover { background: #c0392b; }
        
        .mode-group {
            display: flex;
            gap: 5px;
            margin-bottom: 15px;
        }
        .mode-btn {
            flex: 1;
            font-size: 0.8rem;
            padding: 8px 4px;
            background: var(--bg-input);
            border: 1px solid var(--border);
            color: var(--text-muted);
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
        }
        .mode-btn.active {
            color: #fff;
            background: var(--accent-blue);
            border-color: var(--accent-blue);
        }
        .mode-btn.active.chao { background: var(--accent-orange); border-color: var(--accent-orange); }
        .mode-btn.active.tim { background: var(--accent-green); border-color: var(--accent-green); }
    </style>
</head>
<body>

<div class="container">
    <h1>GROW-SYNC DASHBOARD</h1>

    <!-- SYSTEM STATUS HEADER -->
    <div class="grid" style="grid-template-columns: 1fr;">
        <div class="card" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; padding: 15px 20px;">
            <div>
                <span style="color: var(--text-muted);">ESP-Zeit:</span> 
                <span id="display-rtc-time" style="font-weight: bold; color: var(--accent-orange); margin-right: 20px;">--:--</span>
                <span style="color: var(--text-muted);">WiFi RSSI:</span> 
                <span id="display-rssi" style="font-weight: bold;">-- dBm</span>
            </div>
            <div>
                <span style="color: var(--text-muted); font-size: 0.8rem;">Global Rev: <span id="display-rev">0</span></span>
            </div>
        </div>
    </div>

    <div class="grid">
        <!-- SEKTION 1: BELEUCHTUNG -->
        <div class="card">
            <h2>Licht-Steuerung</h2>
            <div class="status-val"><span id="txt-light-pct">--</span>%</div>
            <div class="sub-text" id="txt-light-hint">Lade Status...</div>
            
            <div class="mode-group">
                <button class="mode-btn" id="lmode-man" onclick="setLightMode('man')">MANU</button>
                <button class="mode-btn" id="lmode-tim" onclick="setLightMode('tim')">TIMER</button>
            </div>

            <div class="form-group">
                <label>Manuelle Helligkeit (Min. 25%)</label>
                <input type="range" id="slider-light" min="25" max="100" value="25" onchange="sendLightPct(this.value)">
            </div>
            
            <div class="btn btn-danger" style="display:block;" onclick="emergencyLightStop()">LICHT NOT-AUS (0%)</div>
            
            <h3 style="font-size:1rem; margin-top:20px; border-bottom: 1px solid var(--border); padding-bottom:5px;">Timer Konfig</h3>
            <div class="form-group">
                <label>Startzeit (HH:MM)</label>
                <div class="row">
                    <input type="number" id="input-l-h" min="0" max="23" placeholder="HH">
                    <span>:</span>
                    <input type="number" id="input-l-m" min="0" max="59" placeholder="MM">
                </div>
            </div>
            <div class="form-group">
                <label>Dauer / Sonnen-Zeiten (Minuten)</label>
                <div class="row">
                    <input type="number" id="input-l-dur" min="1" placeholder="Laufzeit Min">
                </div>
                <div class="row" style="margin-top: 5px;">
                    <input type="number" id="input-l-sunrise" min="0" placeholder="Aufgang Min">
                    <input type="number" id="input-l-sunset" min="0" placeholder="Untergang Min">
                </div>
            </div>
            <div class="form-group">
                <label>Humidity Modulation Plateau (%)</label>
                <div class="row">
                    <input type="number" id="input-l-hmin" min="0" max="100" placeholder="Min">
                    <input type="number" id="input-l-hmax" min="0" max="100" placeholder="Max">
                </div>
            </div>
            <button class="btn btn-primary" style="width:100%;" onclick="saveLightTimer()">Timer Speichern</button>
        </div>

        <!-- SEKTION 2: ABLUFT (EXHAUST) -->
        <div class="card">
            <h2>Abluft-Ventilator</h2>
            <div class="status-val"><span id="txt-ex-pct">--</span>%</div>
            <div class="sub-text">RPM: <span id="txt-ex-rpm">--</span> | Ist-Speed: <span id="txt-ex-speednow">--</span>%</div>
            <div class="sub-text" style="color:var(--accent-orange);" id="txt-ex-reason">Reason: --</div>

            <div class="mode-group">
                <button class="mode-btn" id="exmode-man" onclick="setExhaustMode('man')">MANUELL</button>
                <button class="mode-btn" id="exmode-auto" onclick="setExhaustMode('auto')">AUTO</button>
            </div>

            <div class="form-group">
                <label>Manuelle Leistung / Mindestdrehzahl</label>
                <div class="row">
                    <input type="number" id="input-ex-pct" min="0" max="100" placeholder="Leistung %" onchange="sendExhaustSpeeds()">
                    <input type="number" id="input-ex-min" min="0" max="100" placeholder="Minimum %" onchange="sendExhaustSpeeds()">
                </div>
            </div>

            <div class="form-group" style="background: rgba(230,126,34,0.1); padding: 10px; border-radius: 6px; border: 1px solid rgba(230,126,34,0.3);">
                <label style="color: var(--accent-orange); font-weight: bold;">Chaos-Modus Flag</label>
                <div class="row">
                    <select id="select-ex-chaos" onchange="sendExhaustChaos(this.value)">
                        <option value="false">Inaktiv</option>
                        <option value="true">Chaos Aktivieren</option>
                    </select>
                </div>
            </div>

            <h3 style="font-size:1rem; margin-top:15px; border-bottom: 1px solid var(--border); padding-bottom:5px;">Klima Targets</h3>
            <div class="form-group">
                <label>Temperatur (°C Min / Max)</label>
                <div class="row">
                    <input type="number" step="0.1" id="target-temp-min">
                    <input type="number" step="0.1" id="target-temp-max">
                </div>
            </div>
            <div class="form-group">
                <label>Luftfeuchtigkeit (% Min / Max)</label>
                <div class="row">
                    <input type="number" id="target-hum-min">
                    <input type="number" id="target-hum-max">
                </div>
            </div>
            <div class="form-group">
                <label>VPD (kPa Min / Max)</label>
                <div class="row">
                    <input type="number" step="0.1" id="target-vpd-min">
                    <input type="number" step="0.1" id="target-vpd-max">
                </div>
            </div>
            <button class="btn btn-primary" style="width:100%;" onclick="saveExhaustTargets()">Klima Targets Speichern</button>
        </div>

        <!-- SEKTION 3: UMLUFT & LIVE SENSOREN (INKL. BLE) -->
        <div class="card">
            <h2>Umluft-Ventilator</h2>
            <div class="status-val"><span id="txt-circ-pct">--</span>%</div>
            <div class="sub-text">RPM: <span id="txt-circ-rpm">--</span> | Ist-Speed: <span id="txt-circ-speednow">--</span>%</div>
            
            <div class="mode-group">
                <button class="mode-btn" id="cmode-man" onclick="setCircMode('man')">MANU</button>
                <button class="mode-btn" id="cmode-nat" onclick="setCircMode('nat')">NAT</button>
                <button class="mode-btn" id="cmode-chao" onclick="setCircMode('chao')">CHAO</button>
            </div>
            <div class="form-group">
                <label>Manuelle Leistung / Mindestdrehzahl</label>
                <div class="row">
                    <input type="number" id="input-circ-pct" min="0" max="100" placeholder="Speed %" onchange="sendCircSettings()">
                    <input type="number" id="input-circ-min" min="0" max="100" placeholder="Min %" onchange="sendCircSettings()">
                </div>
            </div>

            <h2>Kabel-Sensoren</h2>
            <table style="width: 100%; font-size: 0.9rem; border-collapse: collapse; margin-bottom: 20px;">
                <tr style="border-bottom: 1px solid var(--border);"><td style="padding:6px 0; color:var(--text-muted);">Temp Innen/Außen:</td><td style="text-align:right; font-weight:bold;"><span id="val-temp-in">--</span>°C / <span id="val-temp-ext">--</span>°C</td></tr>
                <tr style="border-bottom: 1px solid var(--border);"><td style="padding:6px 0; color:var(--text-muted);">Feuchte Innen/Außen:</td><td style="text-align:right; font-weight:bold;"><span id="val-hum-in">--</span>% / <span id="val-hum-ext">--</span>%</td></tr>
                <tr style="border-bottom: 1px solid var(--border);"><td style="padding:6px 0; color:var(--text-muted);">Blatttemperatur:</td><td style="text-align:right; font-weight:bold; color:var(--accent-green);"><span id="val-temp-leaf">--</span>°C</td></tr>
                <tr><td style="padding:6px 0; color:var(--text-muted);">Batterie-Spannung:</td><td style="text-align:right; font-weight:bold;"><span id="val-vbat">--</span> V</td></tr>
            </table>

            <!-- NEU: BLE SENSOR MATRIX -->
            <h2>BLE Funk-Sensoren</h2>
            <table style="width: 100%; font-size: 0.9rem; border-collapse: collapse;">
                <!-- SPS SENSOR -->
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding:6px 0; font-weight:bold;">Sensor SPS:</td>
                    <td style="text-align:right; font-weight:bold;" id="val-sps-status">--</td>
                </tr>
                <tr style="border-bottom: 1px solid var(--border); background: rgba(255,255,255,0.02);">
                    <td style="padding:6px 0; padding-left:15px; color:var(--text-muted);">Klima SPS:</td>
                    <td style="text-align:right; font-weight:bold;"><span id="val-sps-temp">--</span> / <span id="val-sps-hum">--</span></td>
                </tr>
                <!-- TB2 SENSOR -->
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding:6px 0; font-weight:bold;">Sensor TB2:</td>
                    <td style="text-align:right; font-weight:bold;" id="val-tb2-status">--</td>
                </tr>
                <tr style="background: rgba(255,255,255,0.02);">
                    <td style="padding:6px 0; padding-left:15px; color:var(--text-muted);">Klima TB2:</td>
                    <td style="text-align:right; font-weight:bold;"><span id="val-tb2-temp">--</span> / <span id="val-tb2-hum">--</span></td>
                </tr>
            </table>
        </div>
    </div>
</div>

<script>
    // REVISIONS VERWALTUNG (Synchronisiert mit dem ESP)
    let globalRev = 0;
    let revLight = 0;
    let revExhaust = 0;
    let revCircfan = 0;
    let isInitialLoad = true;

    // Zentraler Daten-Abruf (GET)
    async function updateDashboard() {
        try {
            const response = await fetch('/data');
            if (!response.ok) return;
            const data = await response.json();

            // Globale System-Revision
            globalRev = data.rev || 0;
            document.getElementById('display-rev').innerText = globalRev;

            // WiFi RSSI Auswertung
            const rssi = parseInt(data.health?.signal?.rssi);
            const rssiEl = document.getElementById('display-rssi');
            if (rssi === -256 || isNaN(rssi)) {
                rssiEl.innerText = "OFFLINE";
                rssiEl.style.color = "var(--accent-red)";
            } else {
                rssiEl.innerText = rssi + " dBm";
                rssiEl.style.color = rssi > -70 ? "var(--accent-green)" : "var(--accent-orange)";
            }
            document.getElementById('display-rtc-time').innerText = data.rtc_time || "offline";

            // --- 1. INITIALISIERUNGS-PHASE (ABGLEICH BEIM ERSTEN ERFOLGREICHEN REFRESH) ---
            if (isInitialLoad) {
                // Lokale Revisions-Zähler an den echten ESP-Stand anpassen (Dein Absolutes Gesetz!)
                revLight = data.rev_light || 0;
                revExhaust = data.rev_exhaust || 0;
                revCircfan = data.rev_circfan || 0;

                // Inputs einmalig mit den Werten vom ESP befüllen
                document.getElementById('input-l-h').value = data.l_start_h;
                document.getElementById('input-l-m').value = data.l_start_m;
                document.getElementById('input-l-dur').value = data.l_dur;
                document.getElementById('input-l-sunrise').value = data.l_sunrise;
                document.getElementById('input-l-sunset').value = data.l_sunset;
                document.getElementById('input-l-hmin').value = data.light_humidity_min;
                document.getElementById('input-l-hmax').value = data.light_humidity_max;

                document.getElementById('input-ex-pct').value = data.exhaust_fan_pct;
                document.getElementById('input-ex-min').value = data.exhaust_fan_min;
                document.getElementById('target-temp-min').value = data.target_temp_min;
                document.getElementById('target-temp-max').value = data.target_temp_max;
                document.getElementById('target-hum-min').value = data.target_humidity_min;
                document.getElementById('target-hum-max').value = data.target_humidity_max;
                document.getElementById('target-vpd-min').value = data.target_vpd_min;
                document.getElementById('target-vpd-max').value = data.target_vpd_max;

                document.getElementById('input-circ-pct').value = data.circulation_fan_pct;
                document.getElementById('input-circ-min').value = data.circulation_fan_min;
                
                isInitialLoad = false; // Initialisierung abgeschlossen
            }

            // --- 2. LIVE UPDATES (WERDEN IMMER AUSGEFÜHRT) ---

            // LICHT RENDERING
            if (data.rev_light >= revLight) {
                document.getElementById('txt-light-pct').innerText = data.light_pct;
                document.getElementById('slider-light').value = data.light_pct < 25 ? 25 : data.light_pct;
                document.querySelectorAll('[id^="lmode-"]').forEach(el => el.classList.remove('active', 'tim'));
                const activeLModeBtn = document.getElementById('lmode-' + data.light_mode);
                if (activeLModeBtn) activeLModeBtn.classList.add('active', data.light_mode === 'tim' ? 'tim' : 'active');
                let hint = data.light_mode === 'tim' ? "Wechsel in: " + data.light_remaining + " Min." : "Manueller Modus aktiv.";
                document.getElementById('txt-light-hint').innerText = hint;
            }

            // ABLUFT RENDERING
            if (data.rev_exhaust >= revExhaust) {
                document.getElementById('txt-ex-pct').innerText = data.exhaust_fan_pct;
                document.getElementById('txt-ex-rpm').innerText = data.exhaust_fan_rpm;
                document.getElementById('txt-ex-speednow').innerText = data.exhaust_fan_speed_now;
                document.getElementById('txt-ex-reason').innerText = data.exhaust_fan_state_reason || "Keine";
                document.getElementById('select-ex-chaos').value = data.exhaust_fan_chaos_active ? "true" : "false";
                document.querySelectorAll('[id^="exmode-"]').forEach(el => el.classList.remove('active'));
                const activeExModeBtn = document.getElementById('exmode-' + data.exhaust_fan_mode);
                if (activeExModeBtn) activeExModeBtn.classList.add('active');
            }

            // UMLUFT RENDERING
            if (data.rev_circfan >= revCircfan) {
                document.getElementById('txt-circ-pct').innerText = data.circulation_fan_pct;
                document.getElementById('txt-circ-rpm').innerText = data.circulation_fan_rpm;
                document.getElementById('txt-circ-speednow').innerText = data.circulation_fan_speed_now;
                document.querySelectorAll('[id^="cmode-"]').forEach(el => el.classList.remove('active', 'chao', 'tim'));
                const activeCircModeBtn = document.getElementById('cmode-' + data.circulation_fan_mode);
                if (activeCircModeBtn) {
                    let cls = 'active';
                    if(data.circulation_fan_mode === 'chao') cls = 'chao';
                    if(data.circulation_fan_mode === 'nat') cls = 'tim';
                    activeCircModeBtn.classList.add('active', cls);
                }
            }

            // KABEL-SENSOREN
            document.getElementById('val-temp-in').innerText = data.temp_in?.toFixed(1) || "--";
            document.getElementById('val-temp-ext').innerText = data.temp_ext?.toFixed(1) || "--";
            document.getElementById('val-hum-in').innerText = data.humid_in || "--";
            document.getElementById('val-hum-ext').innerText = data.humid_ext || "--";
            document.getElementById('val-temp-leaf').innerText = data.leaf_temp?.toFixed(1) || "--";
            document.getElementById('val-vbat').innerText = data.vbat?.toFixed(2) || "--";

            // BLE-SENSOREN
            if (data.ble_sensors) {
                const sps = data.ble_sensors.sps;
                const spsStatusEl = document.getElementById('val-sps-status');
                if (sps && sps.online && sps.ble_temp_sps !== -256.0) {
                    spsStatusEl.innerText = "ONLINE (p: " + sps.p + ")";
                    spsStatusEl.style.color = "var(--accent-green)";
                    document.getElementById('val-sps-temp').innerText = sps.ble_temp_sps.toFixed(1) + "°C";
                    document.getElementById('val-sps-hum').innerText = sps.ble_humid_sps + "%";
                } else {
                    spsStatusEl.innerText = "OFFLINE";
                    spsStatusEl.style.color = "var(--accent-red)";
                    document.getElementById('val-sps-temp').innerText = "--";
                    document.getElementById('val-sps-hum').innerText = "--";
                }

                const tb2 = data.ble_sensors.tb2;
                const tb2StatusEl = document.getElementById('val-tb2-status');
                if (tb2 && tb2.online && tb2.ble_temp_tb2 !== -256.0) {
                    tb2StatusEl.innerText = "ONLINE (p: " + tb2.p + ")";
                    tb2StatusEl.style.color = "var(--accent-green)";
                    document.getElementById('val-tb2-temp').innerText = tb2.ble_temp_tb2.toFixed(1) + "°C";
                    document.getElementById('val-tb2-hum').innerText = tb2.ble_humid_tb2 + "%";
                } else {
                    tb2StatusEl.innerText = "OFFLINE";
                    tb2StatusEl.style.color = "var(--accent-red)";
                    document.getElementById('val-tb2-temp').innerText = "--";
                    document.getElementById('val-tb2-hum').innerText = "--";
                }
            }

        } catch (err) {
            console.error("Dashboard Polling Error:", err);
        }
    }

    // Zentrales Senden (POST)
    async function postControl(payload) {
        globalRev++;
        payload["rev"] = globalRev;
        try {
            const response = await fetch('/control_json', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'plain=' + encodeURIComponent(JSON.stringify(payload))
            });
            if (response.ok) {
                // Nach erfolgreichem Absetzen holen wir sofort frische Daten
                await updateDashboard();
            }
        } catch (e) {
            console.error("Transmission Error:", e);
        }
    }

    // --- STRUKTURIERTER STARTABLAUF (ANTI-KOLLISIONS-LOGIK) ---
    window.onload = async () => {
        // 1. Zuerst einmalig Daten abrufen und Revisions-Zähler synchronisieren
        await updateDashboard();
        
        // 2. Erst JETZT, wo die Basis-Revisionen stehen, den Handshake zum ESP senden
        await postControl({ rev_init_light: 1, rev_init_exhaust: 1, rev_init_circfan: 1 });
        
        // 3. Jetzt darf die automatische Hintergrund-Schleife starten (alle 3 Sek.)
        setInterval(updateDashboard, 3000);
    };

    // LICHT ACTIONS
    function sendLightPct(val) { revLight++; postControl({ rev_light: revLight, light_pct: parseInt(val) }); }
    function setLightMode(mode) { revLight++; postControl({ rev_light: revLight, light_mode: mode }); }
    function emergencyLightStop() { revLight++; postControl({ rev_light: revLight, light_stop: 1 }); }
    function saveLightTimer() {
        revLight++;
        postControl({
            rev_light: revLight,
            l_start_h: parseInt(document.getElementById('input-l-h').value),
            l_start_m: parseInt(document.getElementById('input-l-m').value),
            l_dur: parseInt(document.getElementById('input-l-dur').value),
            l_sunrise: parseInt(document.getElementById('input-l-sunrise').value),
            l_sunset: parseInt(document.getElementById('input-l-sunset').value),
            light_humidity_min: parseInt(document.getElementById('input-l-hmin').value),
            light_humidity_max: parseInt(document.getElementById('input-l-hmax').value)
        });
    }

    // ABLUFT ACTIONS
    function setExhaustMode(mode) { revExhaust++; postControl({ rev_exhaust: revExhaust, exhaust_fan_mode: mode }); }
    function sendExhaustSpeeds() {
        revExhaust++;
        postControl({
            rev_exhaust: revExhaust,
            exhaust_fan_pct: parseInt(document.getElementById('input-ex-pct').value),
            exhaust_fan_min: parseInt(document.getElementById('input-ex-min').value)
        });
    }
    function sendExhaustChaos(val) { revExhaust++; postControl({ rev_exhaust: revExhaust, exhaust_fan_chaos: (val === "true") }); }
    function saveExhaustTargets() {
        revExhaust++;
        postControl({
            rev_exhaust: revExhaust,
            target_temp_min: parseFloat(document.getElementById('target-temp-min').value),
            target_temp_max: parseFloat(document.getElementById('target-temp-max').value),
            target_humidity_min: parseInt(document.getElementById('target-hum-min').value),
            target_humidity_max: parseInt(document.getElementById('target-hum-max').value),
            target_vpd_min: parseFloat(document.getElementById('target-vpd-min').value),
            target_vpd_max: parseFloat(document.getElementById('target-vpd-max').value)
        });
    }

    // UMLUFT ACTIONS
    function setCircMode(mode) { revCircfan++; postControl({ rev_circfan: revCircfan, circulation_fan_mode: mode }); }
    function sendCircSettings() {
        revCircfan++;
        postControl({
            rev_circfan: revCircfan,
            circulation_fan_pct: parseInt(document.getElementById('input-circ-pct').value),
            circulation_fan_min: parseInt(document.getElementById('input-circ-min').value)
        });
    }
</script>
</body>
</html>
)rawliteral";

static void handleRootPage() {
    if (!server.authenticate(www_username, www_password)) return server.requestAuthentication();
    server.send_P(200, "text/html", INDEX_HTML);
}

namespace WebServerBrowser {
    void registerRoutes(WebServer& serverInstance) {
        serverInstance.on("/", HTTP_GET, handleRootPage);
        serverInstance.on("/data", HTTP_GET, handleData);
        serverInstance.on("/control_json", HTTP_POST, handleControlJSON);
    }
}