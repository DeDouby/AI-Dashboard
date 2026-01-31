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
            while (running) {
                try {
                    if (scanner == null || callback == null) {
                        scanner = adapter.getBluetoothLeScanner();
                        if (scanner == null) {
                            Log.w(TAG, "Scanner not available, retrying...");
                            Thread.sleep(1000);
                            continue;
                        }
                    }
    
                    // Prüfen, ob Scan noch läuft – einfacher Ansatz:
                    // Bei Android gibt es keine direkte isScanning(), also wir stoppen & starten sicherheitshalber
                    try {
                        scanner.stopScan(callback);
                    } catch (Throwable ignore) {}
    
                    // ScanSettings wie vorher
                    ScanSettings settings = new ScanSettings.Builder()
                            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
                            .setReportDelay(0)
                            .build();
    
                    try {
                        scanner.startScan(null, settings, callback);
                    } catch (Throwable t) {
                        Log.e(TAG, "Watchdog startScan failed", t);
                    }
    
                    Thread.sleep(5000); // Watchdog prüft alle 5 Sekunden
                } catch (Throwable t) {
                    Log.e(TAG, "ScanWatchdog error", t);
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
                    
                            // Rebuild Desktop-like RAW: CompanyID (LE) + payload
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

                    // 3) Fallback: komplette ADV bytes
                    if (raw == null) return;

                    synchronized (lock) {
                        JSONObject obj = last.get(mac);
                        if (obj == null) {
                            obj = new JSONObject();
                            obj.put("address", mac);
                            obj.put("gat_raw", JSONObject.NULL); // niemals anfassen
                        }

                        obj.put("timestamp", ts());
                        obj.put("name", name);
                        obj.put("rssi", rssi);

                        obj.put("adv_raw", raw);
                        obj.put("log_raw", raw);
                        obj.put("note", "raw");

                        last.put(mac, obj);
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
