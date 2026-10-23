"""Sicherheits-Hilfsmittel: Konfigurationswarnungen und Anmeldebremse.

Absichtlich ohne zusaetzliche Abhaengigkeiten und ohne harte Abbrueche: Die
App laeuft auf einem Turnier live, ein Startabbruch wegen einer
Konfigurationswarnung waere schlimmer als die Warnung selbst.
"""
import logging
import time
from threading import Lock

log = logging.getLogger("cupplan.security")

# Werte, die in der Vorlage stehen und in Produktion nichts zu suchen haben
UNSICHERE_SECRET_KEYS = {
    "dev-secret-key",
    "change-me-in-production-please",
    "dev-only-not-a-secret",
    "test",
    "test-secret",
    "",
}
UNSICHERE_PASSWOERTER = {"admin123", "admin", "password", "changeme", ""}


def pruefe_konfiguration(app):
    """Unsichere Konfiguration finden und als Liste von Hinweisen liefern.

    Die Liste landet im Log und (fuer Superadmins) als Banner im Adminbereich.
    """
    warnungen = []

    if app.config.get("SECRET_KEY") in UNSICHERE_SECRET_KEYS:
        warnungen.append(
            "SECRET_KEY ist ein Vorgabewert. Wer ihn kennt, kann sich "
            "beliebige Sitzungs-Cookies selbst ausstellen und sich als "
            "Superadmin anmelden. Bitte in der .env einen langen "
            "Zufallswert setzen (z. B. 'openssl rand -hex 32')."
        )

    if app.config.get("ADMIN_PASSWORD") in UNSICHERE_PASSWOERTER:
        warnungen.append(
            "ADMIN_PASSWORD ist ein Vorgabewert ('admin123' o. ae.). "
            "Das Passwort des Benutzers 'admin' im Adminbereich aendern "
            "und ADMIN_PASSWORD in der .env ersetzen."
        )

    if not app.config.get("SESSION_COOKIE_SECURE") and not app.config.get("CUPPLAN_DEV_MODE"):
        warnungen.append(
            "SESSION_COOKIE_SECURE ist aus. Das Sitzungs-Cookie wird dann "
            "auch ueber unverschluesseltes HTTP uebertragen. Nur aus "
            "lassen, wenn die App bewusst ohne HTTPS laeuft "
            "(COOKIE_SECURE=1 setzen)."
        )

    for warnung in warnungen:
        log.warning("SICHERHEIT: %s", warnung)
    return warnungen


# ──────────────────────────────────────
# Anmeldebremse gegen Passwort-Raten
# ──────────────────────────────────────

class Anmeldebremse:
    """Begrenzt Fehlversuche je Benutzername+IP.

    Haelt den Zustand im Prozessspeicher. Das genuegt, weil CupPlan mit
    genau einem gunicorn-Worker laeuft; nach einem Neustart ist die Bremse
    geloest. Fuer mehrere Worker braeuchte es Redis – siehe ARCHITEKTUR.md.
    """

    def __init__(self, max_versuche=8, sperre_sekunden=300, fenster_sekunden=900):
        self.max_versuche = max_versuche
        self.sperre_sekunden = sperre_sekunden
        self.fenster_sekunden = fenster_sekunden
        self._versuche = {}          # schluessel -> [zeitstempel, ...]
        self._gesperrt_bis = {}      # schluessel -> zeitstempel
        self._lock = Lock()

    def _jetzt(self):
        return time.time()

    def _aufraeumen(self, schluessel, jetzt):
        grenze = jetzt - self.fenster_sekunden
        self._versuche[schluessel] = [
            t for t in self._versuche.get(schluessel, []) if t > grenze
        ]

    def restsperre(self, schluessel):
        """Verbleibende Sperrzeit in Sekunden (0 = nicht gesperrt)."""
        with self._lock:
            jetzt = self._jetzt()
            bis = self._gesperrt_bis.get(schluessel, 0)
            if bis > jetzt:
                return int(bis - jetzt) + 1
            if bis:
                # Sperre abgelaufen: Zaehler zuruecksetzen
                self._gesperrt_bis.pop(schluessel, None)
                self._versuche.pop(schluessel, None)
            return 0

    def fehlversuch(self, schluessel):
        """Fehlversuch zaehlen. Liefert die Sperrzeit, wenn jetzt gesperrt."""
        with self._lock:
            jetzt = self._jetzt()
            self._aufraeumen(schluessel, jetzt)
            self._versuche.setdefault(schluessel, []).append(jetzt)
            if len(self._versuche[schluessel]) >= self.max_versuche:
                self._gesperrt_bis[schluessel] = jetzt + self.sperre_sekunden
                return self.sperre_sekunden
            return 0

    def erfolg(self, schluessel):
        """Nach erfolgreicher Anmeldung alles vergessen."""
        with self._lock:
            self._versuche.pop(schluessel, None)
            self._gesperrt_bis.pop(schluessel, None)

    def zuruecksetzen(self):
        """Nur fuer Tests."""
        with self._lock:
            self._versuche.clear()
            self._gesperrt_bis.clear()


anmeldebremse = Anmeldebremse()

# Bremse fuer das oeffentliche Vereins-Anmeldeformular (je IP).
# Grosszuegiger bemessen: Ein Verein meldet vielleicht drei Mannschaften an,
# und mehrere Vereine koennen hinter derselben IP sitzen (Vereinsheim-WLAN).
formularbremse = Anmeldebremse(
    max_versuche=12, sperre_sekunden=600, fenster_sekunden=3600,
)
