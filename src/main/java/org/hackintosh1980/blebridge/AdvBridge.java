package org.hackintosh1980.blebridge;

import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.le.*;
import android.content.Context;
import android.util.Log;
import android.util.SparseArray;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.Map;
import java.util.HashMap;
import java.util.TimeZone;
import java.util.UUID;

public class AdvBridge {

    private static final String TAG = "AdvBridge";
    private static final long WRITE_INTERVAL_MS = 1200L;
    private static final int RSSI_MIN = -127; // nicht filtern, sonst verschwinden Geräte “gefühlt”

    private static volatile boolean running = false;
    private static volatile long lastPacketTime = 0L; // volatile für Thread-Sicherheit
    private static BluetoothLeScanner scanner;
    private static ScanCallback callback;

    private static File outFile;

    private static final Object lock = new Object();
    private static final Map<String, JSONObject> last = new HashMap<>();

    // -------------------- helpers --------------------
    private static String ts() {
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSZ", Locale.US);
        sdf.setTimeZone(TimeZone.getDefault());
        return sdf.format(new Date());
    }
    private static File getAppDataDir(Context ctx) {
        // EINZIGE WAHRHEIT für Android-Pipeline-Daten
        return new File(ctx.getFilesDir(), "app/data");
    }
    private static String toHex(byte[] v) {
        if (v == null || v.length == 0) return null;
        StringBuilder sb = new StringBuilder();
        for (byte b : v) sb.append(String.format("%02X", b));
        return sb.toString();
    }

    private static String readTextFile(File f) throws Exception {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        FileInputStream fis = new FileInputStream(f);
        try {
            byte[] buf = new byte[4096];
            int n;
            while ((n = fis.read(buf)) > 0) bos.write(buf, 0, n);
        } finally {
            try { fis.close(); } catch (Throwable ignore) {}
        }
        return bos.toString("UTF-8");
    }
    // -------------------- Watchdog / Scan-Stabilität --------------------
    private static Thread scanWatchdog;
    
    private static void startScanWatchdog(Context ctx, BluetoothAdapter adapter) {
        if (scanWatchdog != null && scanWatchdog.isAlive()) return;
    
        scanWatchdog = new Thread(() -> {
            // Initialer Zeitstempel, damit er nicht sofort beim Start feuert
            lastPacketTime = System.currentTimeMillis(); 
            
            while (running) {
                try {
                    // FINETUNING 1: Intervall auf 2 Sek verkürzen für schnellere Reaktion
                    Thread.sleep(2000); 
    
                    long now = System.currentTimeMillis();
                    long silenceDuration = now - lastPacketTime;
    
                    // FINETUNING 2: Schwellenwert auf 3,5 Sek runter. 
                    // Das ist kurz genug um "live" zu wirken, aber lang genug um Paketlücken zu atmen.
                    if (silenceDuration > 3500) {
                        Log.w(TAG, "Watchdog: SHARP RESTART! Silence: " + silenceDuration + "ms");
                        
                        // FINETUNING 3: Direkter Zugriff auf den Adapter für maximale Sicherheit
                        BluetoothLeScanner freshScanner = adapter.getBluetoothLeScanner();
                        
                        if (freshScanner != null && callback != null) {
                            try {
                                // Erst hart stoppen
                                freshScanner.stopScan(callback);
                            } catch (Throwable ignore) {}
    
                            // Kurz warten, damit der BT-Stack Zeit zum Re-Initialisieren hat (wichtig bei Sleep!)
                            Thread.sleep(150);
    
                            ScanSettings settings = new ScanSettings.Builder()
                                    .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
                                    .setCallbackType(ScanSettings.CALLBACK_TYPE_ALL_MATCHES) // Erzwingt jedes Paket
                                    .setMatchMode(ScanSettings.MATCH_MODE_AGGRESSIVE)      // Nicht filtern
                                    .setReportDelay(0)
                                    .build();
                            
                            try {
                                freshScanner.startScan(null, settings, callback);
                                scanner = freshScanner; // Instanz aktualisieren
                                lastPacketTime = System.currentTimeMillis(); // Reset
                            } catch (Throwable t) {
                                Log.e(TAG, "Watchdog: Start failed", t);
                            }
                        }
                    }
                } catch (InterruptedException e) {
                    break;
                } catch (Throwable t) {
                    Log.e(TAG, "Watchdog Error", t);
                }
            }
        }, "AdvScanWatchdog");
    
        scanWatchdog.setDaemon(true);
        scanWatchdog.start();
    }
    // Pre-seed Store aus bestehender Datei → Dump schrumpft NICHT mehr nach Restart
    private static void loadExistingSnapshot() {
        try {
            if (outFile == null || !outFile.exists()) return;
            String txt = readTextFile(outFile).trim();
            if (txt.isEmpty()) return;

            JSONArray arr = new JSONArray(txt);
            for (int i = 0; i < arr.length(); i++) {
                JSONObject o = arr.optJSONObject(i);
                if (o == null) continue;
                String mac = o.optString("address", null);
                if (mac == null || mac.trim().isEmpty()) continue;
                last.put(mac, o);
            }
            Log.i(TAG, "Preload OK: " + last.size() + " entries from existing ble_dump.json");
        } catch (Throwable t) {
            Log.w(TAG, "Preload failed (ignored)", t);
        }
    }

    private static void writeSnapshot() {
        try {
            JSONArray arr = new JSONArray(last.values());
            File tmp = new File(outFile.getAbsolutePath() + ".tmp");
            try (FileOutputStream fos = new FileOutputStream(tmp, false)) {
                fos.write(arr.toString(2).getBytes("UTF-8"));
                fos.flush();
            }
            //noinspection ResultOfMethodCallIgnored
            tmp.renameTo(outFile);
        } catch (Throwable t) {
            Log.e(TAG, "writer", t);
        }
    }

    // -------------------- API --------------------
    // 🔥 EXAKTE SIGNATUR – passt zu bridge_manager.py (AdvBridge.start(ctx))
    public static String start(Context ctx) {
        if (running) return "ALREADY";

        BluetoothAdapter adapter = BluetoothAdapter.getDefaultAdapter();
        if (adapter == null || !adapter.isEnabled()) return "BT_OFF";

        scanner = adapter.getBluetoothLeScanner();
        if (scanner == null) return "NO_SCANNER";

        outFile = new File(getAppDataDir(ctx), "ble_dump.json");


        synchronized (lock) {
            // NICHT clearen → kumuliert bis du es manuell leerst
            loadExistingSnapshot();
        }

        running = true;
        Log.i(TAG, "ADV started → " + outFile.getAbsolutePath());

        ScanSettings settings = new ScanSettings.Builder()
                .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
                .setReportDelay(0)
                .build();

        callback = new ScanCallback() {
            @Override
            public void onScanResult(int type, ScanResult r) {
                if (!running) return;
                
                // Lebenszeichen für den Watchdog setzen
                lastPacketTime = System.currentTimeMillis(); 
              
                try {
                    if (r == null || r.getDevice() == null) return;
                    if (r.getRssi() < RSSI_MIN) return;
        
                    BluetoothDevice d = r.getDevice();
                    ScanRecord rec = r.getScanRecord();
                    if (rec == null) return;

                    String mac  = d.getAddress();
                    String name = (d.getName() != null) ? d.getName() : "(adv)";
                    int rssi    = r.getRssi();

                    String raw = null;

                    // 1) Manufacturer data (ALLE, erstes brauchbares)
                    SparseArray<byte[]> md = rec.getManufacturerSpecificData();
                    if (md != null && md.size() > 0) {
                        for (int i = 0; i < md.size(); i++) {
                            int companyId = md.keyAt(i);
                            byte[] payload = md.valueAt(i);
                            if (payload == null || payload.length == 0) continue;
                    
                            ByteArrayOutputStream bos = new ByteArrayOutputStream();
                            bos.write(companyId & 0xFF);
                            bos.write((companyId >> 8) & 0xFF);
                            bos.write(payload);
                    
                            raw = toHex(bos.toByteArray());
                            break;
                        }
                    }

                    // 2) Service data (Inkbird etc.)
                    if (raw == null) {
                        Map<android.os.ParcelUuid, byte[]> sd = rec.getServiceData();
                        if (sd != null && !sd.isEmpty()) {
                            for (byte[] v : sd.values()) {
                                raw = toHex(v);
                                if (raw != null) break;
                            }
                        }
                    }

                    // 3) Fallback
                    if (raw == null) return;

                    // ------------------------------------------------------------------
                    // AB HIER: DIE IDENTITÄTS-KORREKTUR
                    // ------------------------------------------------------------------
                    synchronized (lock) {
                        String effectiveMac = mac;
                        String effectiveName = name;
                    
                        // NORMALISIERUNG (Wie im Mac-Script)
                        if (raw != null && raw.startsWith("5900A1")) {
                            effectiveMac = "FF:FF:A1:00:00:01"; 
                            effectiveName = "LGS_BROADCAST"; // Name an Desktop-Version anpassen!
                    
                            if (!effectiveMac.equals(mac)) {
                                last.remove(mac);
                            }
                        }

                        // 3. DATEN AKTUALISIEREN
                        JSONObject obj = last.get(effectiveMac);
                        if (obj == null) {
                            obj = new JSONObject();
                            obj.put("address", effectiveMac);
                            obj.put("gat_raw", JSONObject.NULL);
                        }

                        obj.put("timestamp", ts());
                        obj.put("name", effectiveName); // Stabiler Name wird hier gesetzt
                        obj.put("rssi", rssi);
                        obj.put("adv_raw", raw);
                        obj.put("log_raw", raw);
                        obj.put("note", "normalized_broadcast");

                        last.put(effectiveMac, obj);
                    }

                } catch (Throwable t) {
                    Log.e(TAG, "scan", t);
                }
            }
        };

        startScanWatchdog(ctx, adapter);

        try {
            scanner.startScan(null, settings, callback);
        } catch (Throwable t) {
            running = false;
            Log.e(TAG, "startScan failed", t);
            return "ERR_SCAN";
        }

        new Thread(() -> {
            while (running) {
                try {
                    synchronized (lock) { writeSnapshot(); }
                    Thread.sleep(WRITE_INTERVAL_MS);
                } catch (Throwable t) {
                    Log.e(TAG, "writerLoop", t);
                }
            }
        }, "AdvWriter").start();

        return "OK";
    }

    public static void stop() {
        running = false;
        try {
            if (scanner != null && callback != null) scanner.stopScan(callback);
        } catch (Throwable ignore) {}
    
        try {
            if (scanWatchdog != null) scanWatchdog.interrupt();
        } catch (Throwable ignore) {}
    
        Log.i(TAG, "ADV stopped");
    }

    // Optional: wenn du GATT später auf dieselbe Map mergen willst:
    static Object getLock() { return lock; }
    static Map<String, JSONObject> getStore() { return last; }
}
