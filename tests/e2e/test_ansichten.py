"""Browser-Tests: rendern die Ansichten ohne JavaScript-Fehler?

Der eigentliche Wert dieser Tests ist die Fehlersammlung in conftest.py:
Jede Seite, die hier geladen wird, muss ohne JavaScript-Fehler durchlaufen.
Das faengt genau die Fehlerklasse, die die restliche Testsuite nicht sieht –
etwa eine Funktion, die beim Auslagern eines Inline-Skripts verloren ging.
"""
import pytest

from conftest import warte_auf_zustand
from helfer import BASIS, bild


# ──────────────────────────────────────
# Oeffentliche Ansichten
# ──────────────────────────────────────

def test_startseite(seite):
    seite.goto(BASIS)
    assert seite.locator(".tournament-card").count() > 0
    bild(seite, "01-startseite")


def test_live_ansicht(seite, erstes_turnier):
    seite.goto(f"{BASIS}/t/{erstes_turnier}/")
    warte_auf_zustand(seite)

    # Der Zustand muss auch wirklich gerendert sein, nicht nur angekommen
    text = seite.locator("body").inner_text()
    assert "Keine Teams registriert" not in text, (
        "Die Tabelle blieb leer, obwohl der Zustand da ist:\n" + text[:400])
    bild(seite, "02-live-ansicht")


def test_live_ansicht_zeigt_anstosszeiten(seite, erstes_turnier):
    """Die Anstosszeiten aus dem Spielplan muessen im Browser ankommen."""
    seite.goto(f"{BASIS}/t/{erstes_turnier}/")
    warte_auf_zustand(seite)
    text = seite.locator("body").inner_text()
    import re as _re
    assert _re.search(r"\d{2}:\d{2}", text), (
        "Keine Uhrzeit in der Live-Ansicht:\n" + text[:400])


def test_handy_ansicht(seite, erstes_turnier):
    seite.goto(f"{BASIS}/t/{erstes_turnier}/phone/")
    seite.wait_for_selector("#tab-matches", timeout=20000)
    seite.wait_for_function(
        """() => {
            const el = document.getElementById('panel-matches');
            return el && el.innerText.trim().length > 20;
        }""", timeout=25000)
    # Durch alle Tabs klicken – jeder Tab fuehrt eigenes JavaScript aus
    for tab in ("live", "table", "matches", "teams", "rules"):
        knopf = seite.locator(f"#tab-{tab}")
        if knopf.count():
            knopf.click()
            seite.wait_for_timeout(250)
    bild(seite, "03-handy-ansicht")


def test_tv_ansicht(seite, erstes_turnier):
    seite.goto(f"{BASIS}/t/{erstes_turnier}/tv/")
    seite.wait_for_selector("#col-matches-body, .tv-clock", timeout=20000)
    # Warten, bis die Spalte "Spiele" gefuellt ist – sonst sieht man nur
    # den Platzhalter und haelt die Ansicht faelschlich fuer kaputt.
    seite.wait_for_function(
        """() => {
            const el = document.getElementById('col-matches-body');
            return el && el.innerText.trim().length > 20;
        }""", timeout=25000)
    bild(seite, "04-tv-ansicht")


def test_speisekarte(seite):
    seite.goto(f"{BASIS}/speisekarte")
    assert seite.locator(".menu-container, .landing-empty").count() > 0
    bild(seite, "05-speisekarte")


def test_statistik_seite(seite, erstes_turnier):
    seite.goto(f"{BASIS}/t/{erstes_turnier}/statistik")
    seite.wait_for_selector(".st-card", timeout=15000)
    bild(seite, "06-statistik")


def test_platzierung_seite(seite, erstes_turnier):
    seite.goto(f"{BASIS}/t/{erstes_turnier}/platzierung")
    seite.wait_for_selector(".pl-card", timeout=15000)
    bild(seite, "07-platzierung")


def test_anstosszeiten_sind_sichtbar(seite, erstes_turnier):
    """Die Anstosszeiten muessen im Browser tatsaechlich ankommen."""
    seite.goto(f"{BASIS}/t/{erstes_turnier}/phone/")
    seite.click("#tab-matches")
    seite.wait_for_function(
        """() => {
            const el = document.getElementById('panel-matches');
            return el && /\\d{2}:\\d{2}/.test(el.innerText);
        }""", timeout=25000)
    text = seite.locator("#panel-matches").inner_text()
    assert "Uhr" in text, (
        "In der Spieleliste steht keine Anstosszeit. Sichtbarer Text:\n"
        + text[:400])


# ──────────────────────────────────────
# Adminbereich
# ──────────────────────────────────────

def test_anmeldung_funktioniert_im_browser(seite, admin_seite, erstes_turnier):
    """Formular ausfuellen und absenden – wie ein Verein es tut."""
    # Anmeldung oeffnen
    admin_seite.goto(f"{BASIS}/admin/t/{erstes_turnier}/anmeldungen")
    admin_seite.select_option('select[name="registration_open"]', "1")
    admin_seite.click('button[type="submit"]')
    admin_seite.wait_for_timeout(500)

    admin_seite.goto(f"{BASIS}/t/{erstes_turnier}/anmeldung")
    admin_seite.fill("#club_name", "E2E Testverein")
    admin_seite.fill("#contact_name", "Test Person")
    admin_seite.fill("#contact_email", "e2e@example.org")
    bild(admin_seite, "08-anmeldeformular")
    admin_seite.click('button[type="submit"]')

    admin_seite.wait_for_selector(".anm-haken", timeout=15000)
    assert "angekommen" in admin_seite.locator(".anm-card").inner_text()
    bild(admin_seite, "09-anmeldung-danke")


def test_adminliste(admin_seite):
    admin_seite.goto(f"{BASIS}/admin/")
    assert admin_seite.locator(".card").count() > 0
    bild(admin_seite, "10-admin-turnierliste")


@pytest.mark.parametrize("pfad,warten", [
    ("/administration", ".adm-card"),
    ("/design", ".card, .adm-card"),
    ("/organisation", ".card, table"),
    ("/finals-setup", "body"),
    ("/anmeldungen", ".card"),
    ("/statistik", ".card"),
    ("/siegerehrung", ".card"),
    ("/schiedsrichter", ".card"),
])
def test_adminseiten_laufen_ohne_js_fehler(admin_seite, erstes_turnier,
                                           pfad, warten):
    admin_seite.goto(f"{BASIS}/admin/t/{erstes_turnier}{pfad}")
    admin_seite.wait_for_selector(warten, timeout=20000)
    admin_seite.wait_for_timeout(600)      # verzoegertes JavaScript abwarten
    name = pfad.strip("/").replace("/", "-")
    bild(admin_seite, f"11-admin-{name}")


def test_dashboard(admin_seite, erstes_turnier):
    """Das Dashboard hatte das groesste Inline-Skript – jetzt ausgelagert."""
    admin_seite.goto(f"{BASIS}/admin/t/{erstes_turnier}/")
    admin_seite.wait_for_selector("table, .card", timeout=20000)
    admin_seite.wait_for_timeout(1000)
    # Das ausgelagerte Skript muss geladen sein
    geladen = admin_seite.evaluate(
        "() => Array.from(document.scripts).map(s => s.src)"
             ".filter(s => s.includes('admin/dashboard.js')).length")
    assert geladen == 1, "dashboard.js wird nicht geladen"
    bild(admin_seite, "12-admin-dashboard")


def test_spielplan_druckansicht(admin_seite, erstes_turnier):
    admin_seite.goto(f"{BASIS}/admin/t/{erstes_turnier}/schedule/print")
    admin_seite.wait_for_selector(".match-table, .section", timeout=20000)
    bild(admin_seite, "13-spielplan-druck")


def test_urkunden_druckansicht(admin_seite, erstes_turnier):
    admin_seite.goto(f"{BASIS}/admin/t/{erstes_turnier}/urkunden")
    admin_seite.wait_for_selector(".urkunde", timeout=20000)
    assert admin_seite.locator(".urkunde").count() > 0
    bild(admin_seite, "14-urkunden")


def test_schiedsrichter_einsatzplan(admin_seite, erstes_turnier):
    admin_seite.goto(f"{BASIS}/admin/t/{erstes_turnier}/schiedsrichter/plan")
    admin_seite.wait_for_selector(".blatt", timeout=20000)
    bild(admin_seite, "15-schiedsrichter-plan")


def test_login_mit_falschem_passwort(seite):
    seite.goto(f"{BASIS}/admin/login")
    seite.fill('input[name="username"]', "admin")
    seite.fill('input[name="password"]', "garantiert-falsch")
    seite.click('button[type="submit"], input[type="submit"]')
    seite.wait_for_timeout(1000)
    assert "Ungueltige Anmeldedaten" in seite.content() \
        or "Zu viele Fehlversuche" in seite.content()
