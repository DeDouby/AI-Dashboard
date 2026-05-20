import time

class BaseOverlayEngine:
    """
    Zentrale State-Maschine für:
    - Handshake (rev_init)
    - Revision Tracking (rev)
    - Retry Logik
    - Sync Status (Green/Orange/Red)
    """

    def __init__(self):
        self._last_sent_rev = 0
        self._last_send_time = 0
        self._retry_count = 0
        self._max_retries = 5

        self._my_handshake_id = 0
        self._last_adopted_init = None

    # =========================
    # HANDSHAKE
    # =========================
    def create_handshake(self):
        self._my_handshake_id = int(time.time())
        return self._my_handshake_id

    def is_alive(self, server_init):
        return server_init == self._my_handshake_id

    def adopt_new_session(self, server_init, server_rev):
        if self._last_adopted_init != server_init:
            self._last_adopted_init = server_init
            if not self.is_alive(server_init):
                # Fremde Session erkannt -> Wir passen unsere Basis-Revision an,
                # damit wir nicht fälschlicherweise im "pending" State hängenbleiben.
                self._last_sent_rev = server_rev
            return True
        return False

    # =========================
    # REVISION / RETRY
    # =========================
    def mark_sent(self, rev):
        self._last_sent_rev = rev
        self._last_send_time = time.time()

    def is_pending(self, server_rev):
        return self._last_sent_rev > server_rev

    def should_retry(self):
        return (time.time() - self._last_send_time) > 3.0

    def retry_allowed(self):
        return self._retry_count < self._max_retries

    def register_retry(self):
        self._retry_count += 1

    def reset_retry(self):
        self._retry_count = 0

    # =========================
    # SYNC STATE (FIXED FOR MULTI-UI)
    # =========================
    def is_synced(self, server_init, server_rev, user_active, last_user_action):
        # MULTI-UI FIX: Der Server ist valide, wenn überhaupt ein Handshake aktiv ist (> 0)
        server_alive = server_init > 0
        pending = self.is_pending(server_rev)
        time_ok = (time.time() - last_user_action) > 1.5

        # Wir sind synchronisiert, wenn der ESP erreichbar ist, keine lokalen Updates
        # auf Bestätigung warten, der User nicht aktiv schiebt und der Cooldown vorbei ist.
        return server_alive and (not pending) and (not user_active) and time_ok

    def get_status(self, server_init, server_rev, user_active, last_user_action):
        if self.is_synced(server_init, server_rev, user_active, last_user_action):
            self.reset_retry()
            return "green"

        if self.is_pending(server_rev):
            if self.retry_allowed():
                return "retry"
            return "error"

        return "orange"