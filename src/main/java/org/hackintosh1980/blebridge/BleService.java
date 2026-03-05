package org.hackintosh1980.blebridge;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import android.os.Build;
import android.content.Context;
import android.os.PowerManager;
import android.util.Log;

public class BleService extends Service {
    private static final String CHANNEL_ID = "LGS_BRIDGE_CHANNEL";
    private PowerManager.WakeLock wakeLock;

    @Override
    public void onCreate() {
        super.onCreate();
        // CPU wachhalten, damit der Scan nicht stoppt
        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "LGS:WakeLock");
        if (wakeLock != null && !wakeLock.isHeld()) {
            wakeLock.acquire();
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        createNotificationChannel();
        
        // Notification für den Vordergrund erstellen
        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }

        Notification notification = builder
            .setContentTitle("LGS Bridge Aktiv")
            .setContentText("Empfange und sende BLE Daten...")
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setOngoing(true)
            .build();

        // Dem System sagen: Ich bin jetzt ein wichtiger Vordergrund-Dienst!
        startForeground(101, notification);

        // --- BRIDGES STARTEN ---
        // 1. Scanner starten
        AdvBridge.start(this);

        // 2. Broadcast starten (Pfad wird automatisch generiert)
        String mixedPath = getFilesDir().getAbsolutePath() + "/app/data/mixed.json";
        BroadcastBridge.start(this, mixedPath);
    
        Log.i("BleService", "Service gestartet. Pfad: " + mixedPath);

        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        // Aufräumen, wenn der Dienst beendet wird
        AdvBridge.stop();
        BroadcastBridge.stop();
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) { 
        return null; 
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel serviceChannel = new NotificationChannel(
                CHANNEL_ID, 
                "LGS Bridge Service", 
                NotificationManager.IMPORTANCE_LOW
            );
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(serviceChannel);
            }
        }
    }
}