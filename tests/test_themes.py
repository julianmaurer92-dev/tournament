"""Themes: Katalog, Auflösung, Abbildung alter Namen.

Die Gestaltungssprache heisst „Anpfiff" und bringt acht eigene Themes
mit, jedes hell und dunkel, dazu „Anzeigetafel" nur fuer den Beamer.

Der wichtigste Punkt hier: **Niemandem darf seine Einstellung
wegbrechen.** Es gibt inzwischen zwei Generationen alter Namen, und
beide muessen weiter etwas Sinnvolles ergeben – keinen Fehler und
keine leere Seite.
"""
import pytest

from app.models import get_setting
from app.themes import (ALTE_NAMEN, NUR_DUNKEL, SCHEMATA, STANDARD_SCHEMA,
                        STANDARD_THEME, THEMES, aufloesen, katalog,
                        speicherwert)
from tests.conftest import make_tournament


# ── Katalog ────────────────────────────────────────────────────

def test_neun_themes():
    assert len(THEMES) == 9
    for schluessel, daten in THEMES.items():
        assert daten["name"], schluessel
        assert daten["beschreibung"], schluessel
        for schema in SCHEMATA:
            farben = daten["vorschau"][schema]
            assert len(farben) == 3, f"{schluessel}/{schema}"
            for f in farben:
                assert f.startswith("#") and len(f) == 7, f"{schluessel}: {f}"


def test_katalog_traegt_alles_was_die_galerie_braucht():
    eintraege = katalog()
    assert len(eintraege) == len(THEMES)
    for e in eintraege:
        assert set(e) == {"schluessel", "name", "beschreibung",
                          "vorschau", "nur_dunkel"}
    # Die Galerie muss wissen, wo sie den Hell-Schalter sperren soll
    assert [e["schluessel"] for e in eintraege if e["nur_dunkel"]] == list(NUR_DUNKEL)


def test_schluessel_sind_ascii_und_kleingeschrieben():
    """Sie landen in CSS-Selektoren und in der Datenbank."""
    for schluessel in THEMES:
        assert schluessel.isascii()
        assert schluessel.islower()
        assert schluessel.isalpha()


# ── Auflösung ──────────────────────────────────────────────────

def test_leerer_wert_gibt_die_vorgabe():
    for wert in ("", "   ", None):
        assert aufloesen(wert) == (STANDARD_THEME, STANDARD_SCHEMA)


def test_neue_schreibweise():
    assert aufloesen("rasen:dunkel") == ("rasen", "dunkel")
    assert aufloesen("flutlicht:hell") == ("flutlicht", "hell")


def test_theme_ohne_schema_nimmt_das_standardschema():
    assert aufloesen("trikot") == ("trikot", STANDARD_SCHEMA)


def test_unbekanntes_schema_behaelt_das_theme():
    """Das Theme ist die eigentliche Entscheidung – die bleibt."""
    assert aufloesen("bernstein:lila") == ("bernstein", STANDARD_SCHEMA)


def test_unbekanntes_theme_faellt_ganz_zurueck():
    assert aufloesen("quatsch") == (STANDARD_THEME, STANDARD_SCHEMA)
    assert aufloesen("quatsch:hell") == (STANDARD_THEME, STANDARD_SCHEMA)


def test_grossschreibung_egal():
    assert aufloesen("RASEN:DUNKEL") == ("rasen", "dunkel")
    assert aufloesen("  Flutlicht:Hell  ") == ("flutlicht", "hell")


def test_anzeigetafel_hat_keine_helle_variante():
    """Sie hat genau eine Aufgabe: aus zehn Metern lesbar sein."""
    assert aufloesen("anzeigetafel") == ("anzeigetafel", "dunkel")
    assert aufloesen("anzeigetafel:hell") == ("anzeigetafel", "dunkel")
    assert speicherwert("anzeigetafel", "hell") == "anzeigetafel:dunkel"


# ── Alte Namen ─────────────────────────────────────────────────

@pytest.mark.parametrize("alt", sorted(ALTE_NAMEN))
def test_jeder_alte_name_ergibt_ein_gueltiges_theme(alt):
    theme, schema = aufloesen(alt)
    assert theme in THEMES, alt
    assert schema in SCHEMATA, alt


def test_beide_generationen_sind_abgedeckt():
    englisch = {"dark", "midnight", "slate", "ocean", "crimson",
                "light", "navy", "forest", "amber", "violet"}
    deutsch = {"mitternacht", "schiefer", "ozean", "ziegel", "forst",
               "veilchen", "papier", "stadion"}
    assert englisch <= set(ALTE_NAMEN)
    assert deutsch <= set(ALTE_NAMEN)


def test_alte_namen_behalten_ihren_charakter():
    """Wer Dunkles gespeichert hat, soll nichts Helles bekommen."""
    assert aufloesen("dark")[1] == "dunkel"
    assert aufloesen("midnight") == ("nachtspiel", "dunkel")
    assert aufloesen("crimson") == ("trikot", "dunkel")
    assert aufloesen("ziegel") == ("trikot", "dunkel")
    # Die beiden hellen bleiben hell
    assert aufloesen("light")[1] == "hell"
    assert aufloesen("papier")[1] == "hell"
    # Die Beamer-Variante landet auf der Anzeigetafel
    assert aufloesen("stadion") == ("anzeigetafel", "dunkel")


def test_kein_alter_name_kollidiert_mit_einem_neuen():
    """Sonst entscheidet die Reihenfolge im Code, nicht die Absicht."""
    doppelt = set(ALTE_NAMEN) & set(THEMES)
    assert not doppelt, f"Name ist alt UND neu: {doppelt}"


# ── Speicherwert ───────────────────────────────────────────────

def test_speicherwert_und_zurueck():
    for theme in THEMES:
        for schema in SCHEMATA:
            wert = speicherwert(theme, schema)
            zurueck = aufloesen(wert)
            assert zurueck[0] == theme
            if theme in NUR_DUNKEL:
                assert zurueck[1] == "dunkel"
            else:
                assert zurueck[1] == schema


def test_speicherwert_faengt_unsinn_ab():
    assert speicherwert("quatsch", "lila") == speicherwert(
        STANDARD_THEME, STANDARD_SCHEMA)


# ── Zusammenspiel mit der Route ────────────────────────────────

def test_alte_themenamen_werden_beim_speichern_uebersetzt(app, admin_client):
    t = make_tournament("Alt Theme Cup")
    antwort = admin_client.post(f"/admin/t/{t.slug}/api/settings",
                                json={"theme": "midnight"})
    assert antwort.status_code == 200
    assert get_setting(t.id, "theme") == "nachtspiel:dunkel"


def test_alle_neuen_themes_lassen_sich_speichern(app, admin_client):
    """Vorher nahm die Route nur sechs von zehn Namen an – man klickte,
    und es passierte nichts."""
    t = make_tournament("Theme Cup")
    for schluessel in THEMES:
        antwort = admin_client.post(f"/admin/t/{t.slug}/api/settings",
                                    json={"theme": schluessel + ":dunkel"})
        assert antwort.status_code == 200, schluessel
        assert get_setting(t.id, "theme").startswith(schluessel + ":"), schluessel


def test_kaputter_wert_zerlegt_keine_seite(app, admin_client, client):
    t = make_tournament("Kaputt Cup")
    admin_client.post(f"/admin/t/{t.slug}/api/settings", json={"theme": "<script>"})
    assert client.get(f"/t/{t.slug}/").status_code == 200
