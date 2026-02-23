package org.hackintosh1980.blebridge;

import android.bluetooth.BluetoothAdapter;
import android.bluetooth.le.*;
import android.content.Context;
import android.os.ParcelUuid;          // FEHLTE
import android.util.Log;               // FEHLTE
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.UUID;                 // FEHLTE

public class BroadcastBridge {
    private static BluetoothLeAdvertiser advertiser;
    private static AdvertiseCallback activeCallback; 
    private static Thread loopThread;
    private static boolean running = false;
    private static String mixedPath;
    private static byte[] lastPayload = new byte[0]; // Speicher für Vergleich
    private static int packetCounter = 0; // <--- NEU: Der globale Counter
    public static synchronized boolean start(Context ctx, String path) {
        if (running) return true; // Schon an? Dann Finger weg.
        
        mixedPath = path;
        BluetoothAdapter adapter = BluetoothAdapter.getDefaultAdapter();
        if (adapter == null || !adapter.isEnabled()) return false;

        advertiser = adapter.getBluetoothLeAdvertiser();
        if (advertiser == null) return false;

        running = true;
        loopThread = new Thread(() -> loop());
        loopThread.start();
        return true;
    }

    public static synchronized void stop() {
        running = false;
        if (loopThread != null) {
            loopThread.interrupt();
            loopThread = null;
        }
        stopActiveAdvertising();
    }

    private static void stopActiveAdvertising() {
        if (advertiser != null && activeCallback != null) {
            try {
                advertiser.stopAdvertising(activeCallback);
            } catch (Exception ignored) {}
            activeCallback = null;
        }
    }

    private static void loop() {
        while (running) {
            try {
                byte[] currentPayload = encodeMixed();
                
                // NUR senden, wenn Payload sich geändert hat oder noch nie gesendet wurde
                if (currentPayload.length > 0 && !Arrays.equals(currentPayload, lastPayload)) {
                    stopActiveAdvertising();
                    advertise(currentPayload);
                    lastPayload = currentPayload;
                }
                
                Thread.sleep(5000); // Check alle 5 Sek reicht völlig
            } catch (InterruptedException e) {
                break;
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private static void advertise(byte[] payload) {
        activeCallback = new AdvertiseCallback() {};
        
        // 1. Adapter-Name setzen (Wichtig für die Sichtbarkeit)
        BluetoothAdapter adapter = BluetoothAdapter.getDefaultAdapter();
        if (adapter != null) {
            adapter.setName("LGS");
        }

        // 2. Service UUID hinzufügen (Der "Anker" für Android)
        // Wir nutzen eine Standard-UUID (Environmental Sensing), damit der Stack nicht blockiert
        ParcelUuid pUuid = new ParcelUuid(UUID.fromString("0000181A-0000-1000-8000-00805f9b34fb"));
    
        AdvertiseData data = new AdvertiseData.Builder()
                .addServiceUuid(pUuid)                 // Macht das Paket für Android "offiziell"
                .addManufacturerData(0x0059, payload)  // Deine LGS-Daten (5900A1...)
                .setIncludeDeviceName(true)            // Sendet "LGS" mit
                .build();
    
        AdvertiseSettings settings = new AdvertiseSettings.Builder()
                // BALANCED statt LOW_LATENCY, um Interferenzen beim Empfang auf Android zu minimieren
                .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_BALANCED)
                .setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_HIGH)
                .setConnectable(false) // Bleibt Beacon-Modus
                .build();
        
        try {
            advertiser.startAdvertising(settings, data, activeCallback);
            Log.i("BroadcastBridge", "Advertising started: LGS with Service UUID");
        } catch (Exception e) {
            Log.e("BroadcastBridge", "Failed to start advertising", e);
        }
    }

    private static byte[] encodeMixed() {
        try {
            File f = new File(mixedPath);
            if (!f.exists()) return new byte[0];
            String txt = new String(Files.readAllBytes(f.toPath()));
            JSONArray arr = new JSONArray(txt);
            if (arr.length() == 0) return new byte[0];
            JSONObject obj = arr.getJSONObject(0);

            int t = (int)(obj.optDouble("avg_temp", 0) * 100);
            int h = (int)(obj.optDouble("avg_hum", 0) * 100);
            int v = (int)(obj.optDouble("avg_vpd", 0) * 100);

            byte[] data = new byte[8];
            data[0] = (byte)0xA1;
            data[1] = (byte)(t >> 8); data[2] = (byte)t;
            data[3] = (byte)(h >> 8); data[4] = (byte)h;
            data[5] = (byte)(v >> 8); data[6] = (byte)v;
            
            // --- COUNTER LOGIK ---
            packetCounter = (packetCounter + 1) % 256; 
            data[7] = (byte)packetCounter; 
            // ---------------------

            return data;
        } catch (Exception e) { return new byte[0]; }
    }
}