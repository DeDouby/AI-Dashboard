# cam_viewer_mjpeg_fixed.py
import os
import json
import threading
import cv2
from flask import Flask, Response
import webbrowser

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView

import config
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE

# ---------------- Config ----------------
DEFAULT_RTSP_PORT = 554
DEFAULT_LIVE_PATH = "stream1"
CAM_CFG = os.path.join(config.DATA, "cam_config.json")
MJPEG_PORT = 8080

def build_rtsp_url(ip, u, p, path):
    return f"rtsp://{u}:{p}@{ip}:{DEFAULT_RTSP_PORT}/{path}"

# ---------------- Flask MJPEG Server ----------------
app = Flask(__name__)
cap = None  # global VideoCapture

def gen_frames():
    global cap
    while True:
        if cap is None:
            continue
        ret, frame = cap.read()
        if not ret:
            continue
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def run_flask():
    app.run(host="0.0.0.0", port=MJPEG_PORT, threaded=True)

# ---------------- Kivy Panel ----------------
class CamViewerPanel(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)

        # Player Hinweis
        self.label = Label(
            text="📷 Tippe ▶ Start, um Kamera im Browser zu starten",
            halign="center", valign="middle",
            font_size=sp_scaled(20)
        )
        self.add_widget(self.label)

        # Stream URL
        self.stream_url = None

        # Load Config
        cfg = self._load()

        # ------- FORM -------
        form = BoxLayout(orientation="vertical",
                         size_hint_y=None,
                         height=dp_scaled(150),
                         spacing=dp_scaled(8))

        def make_row(label, default):
            row = BoxLayout(size_hint_y=None, height=dp_scaled(40), spacing=dp_scaled(8))
            row.add_widget(Label(text=label, size_hint=(0.3,1), font_size=sp_scaled(16)))
            field = TextInput(text=default, multiline=False, font_size=sp_scaled(16))
            row.add_widget(field)
            return row, field

        r1, self.inp_ip = make_row("Camera IP", cfg.get("ip",""))
        r2, self.inp_user = make_row("Username", cfg.get("user",""))
        r3, self.inp_pwd = make_row("Password", cfg.get("pwd",""))
        self.inp_pwd.password = True

        form.add_widget(r1)
        form.add_widget(r2)
        form.add_widget(r3)
        self.add_widget(form)

        # ------- BUTTONS -------
        btns = BoxLayout(size_hint_y=None, height=dp_scaled(50), spacing=dp_scaled(8))

        b_start = Button(text="▶ Start Live", background_color=(0.2,0.6,0.2,1), font_size=sp_scaled(18))
        b_start.bind(on_release=lambda *_: self.start())

        b_stop = Button(text="■ Stop", background_color=(0.6,0.2,0.2,1), font_size=sp_scaled(18))
        b_stop.bind(on_release=lambda *_: self.stop())

        btns.add_widget(b_start)
        btns.add_widget(b_stop)
        self.add_widget(btns)

        # ------- LOG -------
        self.log = Label(text="RTSP idle.", valign="top", halign="left", size_hint_y=1, font_size=sp_scaled(14))
        self.log.bind(size=lambda *_: setattr(self.log, "text_size", self.log.size))
        scroll = ScrollView(size_hint=(1,1))
        scroll.add_widget(self.log)
        self.add_widget(scroll)

        # Flask Server starten (einmalig)
        self.flask_thread = threading.Thread(target=run_flask, daemon=True)
        self.flask_thread.start()

    # ---------------- Helpers ----------------
    def _load(self):
        os.makedirs(config.DATA, exist_ok=True)
        if not os.path.exists(CAM_CFG):
            return {}
        try:
            return json.load(open(CAM_CFG))
        except:
            return {}

    def _save(self):
        os.makedirs(os.path.dirname(CAM_CFG), exist_ok=True)
        with open(CAM_CFG, "w", encoding="utf-8") as f:
            json.dump({
                "ip": self.inp_ip.text.strip(),
                "user": self.inp_user.text.strip(),
                "pwd": self.inp_pwd.text.strip(),
            }, f, indent=2, ensure_ascii=False)

    def _log(self, msg):
        self.log.text += "\n" + msg

    # ---------------- Start / Stop ----------------
    def start(self):
        global cap
        self._save()

        ip = self.inp_ip.text.strip()
        u = self.inp_user.text.strip()
        p = self.inp_pwd.text.strip()

        if not ip or not u or not p:
            self._log("❌ IP/User/Pass fehlen.")
            return

        rtsp_url = build_rtsp_url(ip, u, p, DEFAULT_LIVE_PATH)
        self._log(f"🎥 Verbinde RTSP: {rtsp_url}")

        # OpenCV VideoCapture starten
        if cap is not None:
            cap.release()
        cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            self._log("❌ RTSP konnte nicht geöffnet werden!")
            cap = None
            return

        # Browser MJPEG URL
        self.stream_url = f"http://localhost:{MJPEG_PORT}/video"
        self._log(f"🌐 Browser URL: {self.stream_url}")

        # 🔹 Dashboard Back deaktiviert 🔹
        try:
            webbrowser.open(self.stream_url)
        except:
            self._log("⚠ Browser konnte nicht geöffnet werden. Öffne manuell.")

    def stop(self):
        global cap
        if cap:
            cap.release()
            cap = None
        self._log("■ Stream gestoppt.")
