"""Browser-Test: ein Turnier im Browser aufsetzen und bedienen.

Deckt die Stellen ab, die nur mit echtem JavaScript funktionieren: der
Dialog des Spielplan-Generators, die Schiedsrichter-Verteilung und die
Ereigniserfassung. Legt dafuer ein eigenes Turnier an und raeumt am Ende
auf, damit die Dev-Instanz nicht zumuellt.
"""
import re
import time

import pytest

from helfer import BASIS, bild

NAME = "E2E Browserlauf"


@pytest.fixture()
def turnier(admin_seite):
    """Turnier anlegen, Slug zurueckgeben, am Ende loeschen."""
    admin_seite.goto(f"{BASIS}/admin/")
    admin_seite.fill('input[name="name"]', NAME)
    admin_seite.locator('form[action*="/admin/tournaments"]').first.locator(
        'button[type="submit"]').click()
    admin_seite.wait_for_timeout(1500)

    # Slug aus der Turnierliste holen
    verweis = admin_seite.locator(f'a[href*="/admin/t/"]').filter(
        has_text=re.compile("")).first
    seiteninhalt = admin_seite.content()
    treffer = re.search(r'/admin/t/(e2e-browserlauf[^/"]*)/', seiteninhalt)
    assert treffer, "Turnier wurde nicht angelegt oder nicht verlinkt"
    slug = treffer.group(1)

    yield slug

    # Aufraeumen ueber die API, nicht ueber die Oberflaeche
    admin_seite.evaluate(
        """async ([basis, slug]) => {
            const liste = await fetch(basis + '/admin/').then(r => r.text());
        }""", [BASIS, slug])
    admin_seite.goto(f"{BASIS}/admin/")
    formular = admin_seite.locator(
        f'form[action*="/delete"]').filter(has_text=re.compile(""))
    # Loeschen laeuft ueber ein confirm() – das bestaetigen wir automatisch
    admin_seite.on("dialog", lambda d: d.accept())
    admin_seite.evaluate(
        """(slug) => {
            for (const f of document.querySelectorAll('form[action*="/delete"]')) {
                const zeile = f.closest('tr, .card, div');
                if (zeile && zeile.innerText.includes('E2E Browserlauf')) {
                    f.submit();
                    return true;
                }
            }
            return false;
        }""", slug)
    admin_seite.wait_for_timeout(1000)


def test_turnier_im_browser_aufsetzen(admin_seite, turnier):
    slug = turnier
    basis = f"{BASIS}/admin/t/{slug}"

    # ── Gruppen und Teams über die Administration ──────────────
    admin_seite.goto(f"{basis}/administration")
    admin_seite.wait_for_selector(".adm-card", timeout=20000)

    for gruppe in ("Gruppe A", "Gruppe B"):
        formular = admin_seite.locator('form[action*="/groups"]').first
        formular.locator('input[name="name"]').fill(gruppe)
        formular.locator('button[type="submit"]').click()
        admin_seite.wait_for_timeout(900)

    for i, team in enumerate(("Rot", "Blau", "Gelb", "Grün")):
        formular = admin_seite.locator('form[action*="/teams"]').first
        formular.locator('input[name="name"]').fill(team)
        auswahl = formular.locator('select[name="group_id"]')
        if auswahl.count():
            # abwechselnd in Gruppe A und B
            optionen = auswahl.locator("option").all_text_contents()
            ziel = "Gruppe A" if i % 2 == 0 else "Gruppe B"
            if any(ziel in o for o in optionen):
                auswahl.select_option(label=re.compile(ziel))
        formular.locator('button[type="submit"]').click()
        admin_seite.wait_for_timeout(900)

    inhalt = admin_seite.content()
    for team in ("Rot", "Blau", "Gelb"):
        assert team in inhalt, f"Team {team} fehlt nach dem Anlegen"
    bild(admin_seite, "20-e2e-administration")

    # ── Spielplan über den Dialog erzeugen ─────────────────────
    admin_seite.click('button:has-text("Spielplan erzeugen")')
    admin_seite.wait_for_selector("#plan-modal.open", timeout=10000)
    admin_seite.select_option("#plan-felder", "2")
    admin_seite.fill("#plan-spielzeit", "10")
    admin_seite.fill("#plan-pause", "5")
    admin_seite.fill("#plan-datum", "2026-11-14")
    admin_seite.fill("#plan-zeit", "09:00")
    bild(admin_seite, "21-e2e-spielplan-dialog")
    admin_seite.click('#plan-modal button:has-text("Spielplan erzeugen")')

    # Rueckmeldung im Dialog abwarten
    admin_seite.wait_for_function(
        """() => {
            const el = document.getElementById('plan-status');
            return el && /Spiele|Fehler|Nichts/.test(el.textContent);
        }""", timeout=20000)
    status = admin_seite.locator("#plan-status").inner_text()
    assert "Fehler" not in status, status
    assert "Spiele" in status, status
    assert "09:00" in status, f"Beginnzeit fehlt in der Rueckmeldung: {status}"

    admin_seite.wait_for_timeout(2500)   # Seite laedt sich neu

    # ── Plan prüfen: keine Doppelbelegungen ────────────────────
    meldungen = []
    admin_seite.on("dialog", lambda d: (meldungen.append(d.message), d.accept()))
    admin_seite.goto(f"{basis}/administration")
    admin_seite.wait_for_selector(".adm-card", timeout=20000)
    admin_seite.click('button:has-text("Plan prüfen")')
    admin_seite.wait_for_timeout(2500)
    assert meldungen, "Die Prüfung hat keine Rückmeldung gegeben"
    assert "sauber" in meldungen[-1], meldungen[-1]

    # ── Schiedsrichter anlegen und verteilen ───────────────────
    admin_seite.goto(f"{basis}/schiedsrichter")
    admin_seite.wait_for_selector(".card", timeout=20000)
    for name in ("E2E Schiri A", "E2E Schiri B"):
        formular = admin_seite.locator('form[action*="/schiedsrichter/neu"]')
        formular.locator('input[name="name"]').fill(name)
        formular.locator('button[type="submit"]').click()
        admin_seite.wait_for_timeout(900)

    admin_seite.click('button:has-text("Lücken füllen")')
    admin_seite.wait_for_function(
        """() => {
            const el = document.getElementById('verteil-status');
            return el && !el.classList.contains('d-none')
                && /eingeteilt|Fehler/.test(el.textContent);
        }""", timeout=20000)
    status = admin_seite.locator("#verteil-status").inner_text()
    assert "Fehler" not in status, status
    assert "eingeteilt" in status, status
    bild(admin_seite, "22-e2e-schiedsrichter")

    admin_seite.wait_for_timeout(2500)

    # ── Ein Spiel live steuern und ein Tor erfassen ────────────
    admin_seite.goto(f"{basis}/")
    admin_seite.wait_for_selector("table", timeout=20000)
    steuerung = admin_seite.locator('a[href*="/control"]').first
    if steuerung.count():
        steuerung.click()
        admin_seite.wait_for_selector("body", timeout=20000)
        bild(admin_seite, "23-e2e-spielsteuerung")

        ereignisse = admin_seite.locator('a:has-text("Ereignisse")').first
        assert ereignisse.count(), "Kein Link zur Ereigniserfassung"
        ereignisse.click()
        admin_seite.wait_for_selector("#ev-art", timeout=20000)

        admin_seite.select_option("#ev-art", "tor")
        admin_seite.fill("#ev-spieler", "E2E Torschütze")
        admin_seite.fill("#ev-minute", "5")
        admin_seite.click('button:has-text("Erfassen")')
        admin_seite.wait_for_timeout(2500)

        assert "E2E Torschütze" in admin_seite.content(), \
            "Das erfasste Tor erscheint nicht in der Liste"
        bild(admin_seite, "24-e2e-ereignisse")

        # ── Statistik zeigt den Schützen ───────────────────────
        admin_seite.goto(f"{basis}/statistik")
        admin_seite.wait_for_selector(".card", timeout=20000)
        assert "E2E Torschütze" in admin_seite.content()
        bild(admin_seite, "25-e2e-statistik")
