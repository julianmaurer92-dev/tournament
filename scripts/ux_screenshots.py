#!/usr/bin/env python
"""Screenshots aller Seiten fuer den Vorher/Nachher-Vergleich.

Laeuft im Playwright-Container gegen die UX-Dev-Instanz:

    docker compose -p cupplan-ux -f docker-compose.ux.yml run --rm \
        -e ZIEL=docs/ux/vorher e2e \
        sh -c "pip install -q 'playwright==1.49.0' && python scripts/ux_screenshots.py"

Umgebungsvariablen:
    ZIEL     Zielordner (Vorgabe: docs/ux/vorher)
    BREITEN  Komma-Liste, Vorgabe "1440,1024,390"
    THEMES   Komma-Liste "dark,light" – schaltet die Turniereinstellung um
"""
import os
import sys
import urllib.request

BASIS = os.environ.get("CUPPLAN_BASE_URL", "http://web:5000")
ZIEL = os.environ.get("ZIEL", "docs/ux/vorher")
BREITEN = [int(b) for b in os.environ.get("BREITEN", "1440,1024,390").split(",")]
ADMIN = os.environ.get("CUPPLAN_ADMIN_USER", "admin")
PASSWORT = os.environ.get("CUPPLAN_ADMIN_PASSWORD", "admin123")

# (Dateiname, Pfad, braucht Login, Wartebedingung)
# Die Wartebedingung verhindert Screenshots von halb geladenen Seiten –
# die Live-Ansichten fuellen sich erst per Socket.IO.
SEITEN = [
    ("01-startseite",        "/",                              False, None),
    ("02-speisekarte",       "/speisekarte",                   False, None),
    ("03-live",              "/t/{slug}/",                     False, "zustand"),
    ("04-handy",             "/t/{slug}/phone/",               False, "phone"),
    ("05-tv",                "/t/{slug}/tv/",                  False, "tv"),
    ("06-statistik",         "/t/{slug}/statistik",            False, None),
    ("07-platzierung",       "/t/{slug}/platzierung",          False, None),
    ("08-anmeldung",         "/t/{offen}/anmeldung",           False, None),
    ("09-login",             "/admin/login",                   False, None),
    ("10-turnierliste",      "/admin/",                        True,  None),
    ("11-dashboard",         "/admin/t/{slug}/",               True,  None),
    ("12-administration",    "/admin/t/{slug}/administration", True,  None),
    ("13-design",            "/admin/t/{slug}/design",         True,  None),
    ("14-organisation",      "/admin/t/{slug}/organisation",   True,  None),
    ("15-spielsteuerung",    "/admin/t/{slug}/matches/{mid}/control", True, None),
    ("16-spielplan-druck",   "/admin/t/{slug}/schedule/print", True,  None),
    ("17-kabinenschilder",   "/admin/t/{slug}/cabin-signs",    True,  None),
    ("18-finals-setup",      "/admin/t/{slug}/finals-setup",   True,  None),
    ("19-anmeldungen",       "/admin/t/{offen}/anmeldungen",   True,  None),
    ("20-statistik-admin",   "/admin/t/{slug}/statistik",      True,  None),
    ("21-siegerehrung",      "/admin/t/{slug}/siegerehrung",   True,  None),
    ("22-urkunden",          "/admin/t/{slug}/urkunden",       True,  None),
    ("23-schiedsrichter",    "/admin/t/{slug}/schiedsrichter", True,  None),
    ("24-benutzer",          "/admin/users",                   True,  None),
    ("25-speisekarte-admin", "/admin/speisekarte",             True,  None),
    ("26-export-import",     "/admin/export-import",           True,  None),
]

WARTEN = {
    "zustand": "() => typeof currentState !== 'undefined' && currentState !== null",
    "phone": ("() => { const el = document.getElementById('panel-matches');"
              " return el && el.innerText.trim().length > 10; }"),
    "tv": ("() => { const el = document.getElementById('col-matches-body');"
           " return el && el.innerText.trim().length > 10; }"),
}


def _json(pfad):
    with urllib.request.urlopen(f"{BASIS}{pfad}", timeout=20) as antwort:
        import json
        return json.load(antwort)


def ermittle_turniere():
    """Slug des beendeten Turniers, eines mit offener Anmeldung, und eine Spiel-ID."""
    import json
    import re
    with urllib.request.urlopen(f"{BASIS}/", timeout=20) as a:
        html = a.read().decode()
    slugs = re.findall(r'/t/([a-z0-9-]+)/"', html)
    if not slugs:
        sys.exit("Keine Turniere gefunden – erst Seed-Daten anlegen.")
    slug = slugs[0]
    offen = slugs[-1]
    zustand = _json(f"/t/{slug}/api/state")
    spiele = (zustand["past_matches"] + zustand["upcoming_matches"]
              + zustand["final_matches"])
    mid = spiele[0]["id"] if spiele else 0
    return slug, offen, mid


def main():
    from playwright.sync_api import sync_playwright

    slug, offen, mid = ermittle_turniere()
    print(f"Turnier: {slug} · Anmeldung offen: {offen} · Spiel-ID: {mid}")
    os.makedirs(ZIEL, exist_ok=True)

    fehler = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for breite in BREITEN:
            kontext = browser.new_context(
                viewport={"width": breite, "height": 900 if breite > 500 else 844},
                device_scale_factor=1,
                is_mobile=breite <= 500,
                has_touch=breite <= 500,
            )
            seite = kontext.new_page()
            seite.on("pageerror", lambda e, b=breite: fehler.append(f"{b}px {e}"))

            # Anmelden (einmal je Kontext)
            seite.goto(f"{BASIS}/admin/login", timeout=30000)
            seite.fill('input[name="username"]', ADMIN)
            seite.fill('input[name="password"]', PASSWORT)
            seite.click('button[type="submit"], input[type="submit"]')
            seite.wait_for_timeout(1200)

            for name, pfad, _login, warten in SEITEN:
                url = BASIS + pfad.format(slug=slug, offen=offen, mid=mid)
                try:
                    seite.goto(url, timeout=30000, wait_until="domcontentloaded")
                    if warten:
                        try:
                            seite.wait_for_function(WARTEN[warten], timeout=15000)
                        except Exception:
                            pass          # Platzhalter ist besser als Abbruch
                    seite.wait_for_timeout(800)
                    datei = f"{ZIEL}/{name}-{breite}.png"
                    seite.screenshot(path=datei, full_page=True)
                    print(f"  {breite:>4}px  {name}")
                except Exception as e:
                    print(f"  {breite:>4}px  {name}  FEHLER: {str(e)[:90]}")
                    fehler.append(f"{name}@{breite}: {str(e)[:90]}")
            kontext.close()
        browser.close()

    print(f"\nFertig: {ZIEL}")
    if fehler:
        print(f"{len(fehler)} Auffaelligkeiten:")
        for f in fehler[:15]:
            print("  -", f)


if __name__ == "__main__":
    main()
