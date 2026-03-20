[app]
title = ForeGroundtest
package.name = foregroundtest
package.domain = org.hackintosh1980
#####undbedingt ble service.py abändern bei namensänderung!und ja keine binde und unterstriche verwenden!


source.include_exts = py,kv,png,jpg,json,ttf
include_patterns = garden/**/*
source.include_dirs = garden
source.dir = .

version = 1.1
package.version_code = 1
icon.filename = assets/logo.png
presplash.filename = assets/pre_splash.png
#presplash.keep_ratio = True
presplash.color = black
orientation = landscape
fullscreen = 1

# Nur Font Awesome Solid soll eingebunden werden
android.add_assets = assets/fonts/fa-solid-900.ttf
requirements = python3,kivy,pyjnius,pillow,certifi,six,kivy_garden.graph,flask

# (list) Services to declare
android.add_src = src/main/java
services = ble_service:services/ble_service.py


android.permissions = BLUETOOTH, BLUETOOTH_ADMIN, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, BLUETOOTH_SCAN, BLUETOOTH_CONNECT, BLUETOOTH_ADVERTISE, FOREGROUND_SERVICE, FOREGROUND_SERVICE_CONNECTED_DEVICE, POST_NOTIFICATIONS, WAKE_LOCK, REQUEST_IGNORE_BATTERY_OPTIMIZATIONS




android.api = 33
android.minapi = 29
android.ndk_api = 29
android.debug = True
android.archs = arm64-v8a
android.sdk_path = /home/domi/.buildozer/android/platform/android-sdk
android.ndk_path = /home/domi/.buildozer/android/platform/android-ndk-r28c

p4a.source_dir = ~/python-for-android
p4a.build_threads = 6
p4a.extra_args = --allow-minsdk-ndkapi-mismatch
android.gradle_version = 8.0.2
android.build_tools_version = 34.0.0
android.logcat_filters = *:I python:D
