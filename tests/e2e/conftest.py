"""Fixtures fuer die Browser-Tests.

Diese Tests laufen gegen die laufende Dev-Instanz (Service "web" im
Compose-Projekt cupplan-dev), nicht gegen eine eigene Datenbank. Sie sind
damit die einzige Teststufe, die wirklich sieht, was im Browser passiert:
ob JavaScript Fehler wirft, ob Socket.IO verbindet, ob eine Seite leer
bleibt.

Starten:
    docker compose -p cupplan-dev -f docker-compose.dev.yml run --rm e2e
"""
import re

import pytest

from helfer import ADMIN, BASIS, PASSWORT, ist_harmlos

@pytest.fixture()
def seite(page):
    """Browser-Seite, die JavaScript-Fehler sammelt.

    Jeder Test, der diese Fixture nutzt, schlaegt fehl, wenn die Seite einen
    JavaScript-Fehler wirft – genau das, was beim Auslagern der
    Inline-Skripte schiefgehen koennte.
    """
    fehler = []
    page.on("pageerror", lambda e: fehler.append(f"pageerror: {e}"))
    page.on("console", lambda m: (
        fehler.append(f"console.error: {m.text}")
        if m.type == "error" and not ist_harmlos(m.text) else None))
    page.fehler = fehler
    yield page
    assert not fehler, "JavaScript-Fehler auf der Seite:\n" + "\n".join(fehler)


@pytest.fixture()
def admin_seite(seite):
    """Seite, die als Superadmin angemeldet ist."""
    seite.goto(f"{BASIS}/admin/login")
    seite.fill('input[name="username"]', ADMIN)
    seite.fill('input[name="password"]', PASSWORT)
    seite.click('button[type="submit"], input[type="submit"]')
    seite.wait_for_url(re.compile(r"/admin/?$"), timeout=15000)
    return seite


def warte_auf_zustand(seite, timeout=25000):
    """Warten, bis der Turnierzustand im Browser angekommen ist.

    Die Live-Ansichten liefern beim ersten Aufruf nur Platzhalter
    ("Noch keine Spiele beendet"); die echten Daten kommen erst ueber
    Socket.IO. Wer zu frueh prueft oder einen Screenshot macht, sieht eine
    leere Seite und haelt sie faelschlich fuer kaputt.
    """
    seite.wait_for_function(
        "() => typeof currentState !== 'undefined' && currentState !== null"
        " && Array.isArray(currentState.groups)",
        timeout=timeout)
    seite.wait_for_timeout(300)      # ein Render-Durchlauf


@pytest.fixture()
def erstes_turnier(seite):
    """Slug des ersten Turniers auf der Startseite."""
    seite.goto(BASIS)
    verweis = seite.locator('a.tournament-card[href*="/t/"]').first
    verweis.wait_for(timeout=15000)
    href = verweis.get_attribute("href")
    treffer = re.search(r"/t/([^/]+)/", href)
    assert treffer, f"Kein Turnier-Slug in {href}"
    return treffer.group(1)
