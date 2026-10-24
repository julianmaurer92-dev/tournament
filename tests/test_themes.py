"""Tests fuer den Theme-Katalog und die Abbildung der alten Namen."""
import pytest

from app.themes import (
    ALTE_NAMEN, SCHEMATA, STANDARD_SCHEMA, STANDARD_THEME, THEMES,
    aufloesen, katalog, speicherwert,
)


# ──────────────────────────────────────
# Katalog
# ──────────────────────────────────────

def test_zehn_themes_mit_beiden_schemata():
    assert len(THEMES) == 10
    for schluessel, daten in THEMES.items():
        assert set(daten["vorschau"]) == {"hell", "dunkel"}, schluessel
        for schema, farben in daten["vorschau"].items():
            assert len(farben) == 3, f"{schluessel}/{schema}"
            for farbe in farben:
                assert farbe.startswith("#") and len(farbe) == 7, farbe


def test_jedes_theme_hat_name_und_beschreibung():
    for schluessel, daten in THEMES.items():
        assert daten["name"] and len(daten["name"]) >= 4, schluessel
        assert daten["beschreibung"].endswith("."), schluessel
        assert len(daten["beschreibung"]) > 15, schluessel


def test_katalog_behaelt_die_reihenfolge():
    eintraege = katalog()
    assert [e["schluessel"] for e in eintraege] == list(THEMES)
    assert eintraege[0]["schluessel"] == STANDARD_THEME


# ──────────────────────────────────────
# Alte Namen bleiben gueltig
# ──────────────────────────────────────

@pytest.mark.parametrize("alt", sorted(ALTE_NAMEN))
def test_alter_name_ergibt_gueltiges_theme(alt):
    theme, schema = aufloesen(alt)
    assert theme in THEMES
    assert schema in SCHEMATA


def test_alte_namen_behalten_ihren_charakter():
    """midnight war fast schwarz und bleibt dunkel, light bleibt hell."""
    assert aufloesen("midnight") == ("mitternacht", "dunkel")
    assert aufloesen("slate") == ("schiefer", "dunkel")
    assert aufloesen("light")[1] == "hell"
    assert aufloesen("ocean") == ("ozean", "dunkel")
    assert aufloesen("amber") == ("bernstein", "dunkel")


def test_alle_zehn_alten_namen_sind_abgedeckt():
    """Die Designseite bot zehn Themes an – keines darf wegfallen."""
    frueher = {"dark", "midnight", "slate", "ocean", "crimson",
               "light", "navy", "forest", "amber", "violet"}
    assert frueher <= set(ALTE_NAMEN)


# ──────────────────────────────────────
# Aufloesen
# ──────────────────────────────────────

def test_neue_schreibweise():
    assert aufloesen("ozean:hell") == ("ozean", "hell")
    assert aufloesen("stadion:dunkel") == ("stadion", "dunkel")


def test_theme_ohne_schema():
    assert aufloesen("veilchen") == ("veilchen", STANDARD_SCHEMA)


def test_papier_ist_von_haus_aus_hell():
    """Ein Theme namens Papier in Dunkel waere eine Ueberraschung."""
    assert aufloesen("papier") == ("papier", "hell")


@pytest.mark.parametrize("eingabe", ["", None, "   ", "gibtsnicht", "::",
                                     "<script>", "rasen"])
def test_unsinn_faellt_auf_die_vorgabe_zurueck(eingabe):
    """Ein kaputter Wert in der Datenbank darf keine Seite weiss machen.

    "ozean:lila" steht bewusst NICHT in dieser Liste: Dort ist das Theme
    gueltig und nur das Schema nicht. Dann das Theme zu behalten ist
    besser, als alles wegzuwerfen – siehe den naechsten Test.
    """
    assert aufloesen(eingabe) == (STANDARD_THEME, STANDARD_SCHEMA)


def test_unbekanntes_schema_behaelt_das_theme():
    assert aufloesen("ozean:quatsch") == ("ozean", STANDARD_SCHEMA)


def test_grossschreibung_egal():
    assert aufloesen("OZEAN:HELL") == ("ozean", "hell")
    assert aufloesen("  Midnight ") == ("mitternacht", "dunkel")


# ──────────────────────────────────────
# Speichern
# ──────────────────────────────────────

def test_speicherwert_und_zurueck():
    for theme in THEMES:
        for schema in SCHEMATA:
            wert = speicherwert(theme, schema)
            assert aufloesen(wert) == (theme, schema)


def test_speicherwert_faengt_unsinn_ab():
    assert speicherwert("gibtsnicht", "quatsch") == \
        f"{STANDARD_THEME}:{STANDARD_SCHEMA}"


# ──────────────────────────────────────
# Ueber die Route
# ──────────────────────────────────────

def test_alle_zehn_themes_lassen_sich_speichern(app, admin_client):
    """Vorher nahm die Route nur sechs der zehn angebotenen Themes an."""
    from app.models import get_setting
    from tests.conftest import make_tournament
    t = make_tournament("Theme Cup")
    for theme in THEMES:
        for schema in SCHEMATA:
            wert = speicherwert(theme, schema)
            resp = admin_client.post(f"/admin/t/{t.slug}/api/settings",
                                     json={"theme": wert})
            assert resp.status_code == 200, f"{wert}: {resp.data[:200]}"
            assert get_setting(t.id, "theme") == wert


def test_alte_themenamen_werden_beim_speichern_uebersetzt(app, admin_client):
    from app.models import get_setting
    from tests.conftest import make_tournament
    t = make_tournament("Alt Theme Cup")
    resp = admin_client.post(f"/admin/t/{t.slug}/api/settings",
                             json={"theme": "midnight"})
    assert resp.status_code == 200
    assert get_setting(t.id, "theme") == "mitternacht:dunkel"


def test_kaputtes_theme_wird_nicht_gespeichert_sondern_ersetzt(app, admin_client):
    from app.models import get_setting
    from tests.conftest import make_tournament
    t = make_tournament("Kaputt Theme Cup")
    admin_client.post(f"/admin/t/{t.slug}/api/settings",
                      json={"theme": "<script>alert(1)</script>"})
    gespeichert = get_setting(t.id, "theme")
    assert gespeichert == f"{STANDARD_THEME}:{STANDARD_SCHEMA}"
    assert "<" not in gespeichert
