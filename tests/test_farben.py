"""Tests fuer die Vereinsfarben-Palette (reine Rechnerei, ohne Datenbank)."""
import pytest

from app.farben import (
    als_css, kontrast, lesbare_schrift, palette, taugt_als_akzent,
)


# ──────────────────────────────────────
# Lesbare Schrift auf der Vereinsfarbe
# ──────────────────────────────────────

@pytest.mark.parametrize("farbe,erwartet", [
    ("#ffdd00", "#111111"),   # knallgelb -> schwarze Schrift
    ("#f5f5f5", "#111111"),   # fast weiss
    ("#0b1120", "#ffffff"),   # fast schwarz
    ("#1769d4", "#ffffff"),   # kraeftiges Blau
    ("#22c55e", "#111111"),   # helles Gruen
    ("#7c2d12", "#ffffff"),   # dunkles Braun
])
def test_schriftfarbe_folgt_dem_kontrast(farbe, erwartet):
    assert lesbare_schrift(farbe) == erwartet


def test_schriftfarbe_erreicht_immer_lesbaren_kontrast():
    """Fuer jede Farbe muss die gewaehlte Schrift mindestens 4.5:1 haben
    – oder zumindest die bessere der beiden Moeglichkeiten sein."""
    from app.farben import _als_rgb
    schlechteste = 21.0
    for r in range(0, 256, 51):
        for g in range(0, 256, 51):
            for b in range(0, 256, 51):
                hexwert = "#%02x%02x%02x" % (r, g, b)
                schrift = lesbare_schrift(hexwert)
                v = kontrast(_als_rgb(hexwert), _als_rgb(schrift))
                schlechteste = min(schlechteste, v)
                # Die Wahl muss die bessere der beiden Varianten sein
                andere = "#111111" if schrift == "#ffffff" else "#ffffff"
                assert v >= kontrast(_als_rgb(hexwert), _als_rgb(andere)) - 0.001
    # Mittelgraue Farben sind rechnerisch die schwierigsten
    assert schlechteste > 3.0, f"schlechtester Fall nur {schlechteste:.2f}:1"


# ──────────────────────────────────────
# Palette
# ──────────────────────────────────────

def test_palette_vollstaendig():
    p = palette("#1769d4")
    assert set(p) == {
        "vereinsfarbe", "vereinsfarbe-hell", "vereinsfarbe-leise",
        "vereinsfarbe-rand", "vereinsfarbe-text",
    }
    assert p["vereinsfarbe"] == "#1769d4"
    assert p["vereinsfarbe-text"] == "#ffffff"
    assert p["vereinsfarbe-leise"].startswith("rgba(23, 105, 212")


def test_hover_wird_im_dunklen_schema_heller():
    dunkel = palette("#1769d4", "dunkel")["vereinsfarbe-hell"]
    hell = palette("#1769d4", "hell")["vereinsfarbe-hell"]
    from app.farben import _als_rgb, leuchtdichte
    basis = leuchtdichte(_als_rgb("#1769d4"))
    assert leuchtdichte(_als_rgb(dunkel)) > basis
    assert leuchtdichte(_als_rgb(hell)) < basis


@pytest.mark.parametrize("eingabe", ["", None, "blau", "#12", "#1234567",
                                     "rgb(1,2,3)", "  "])
def test_unsinnige_eingabe_ergibt_keine_palette(eingabe):
    assert palette(eingabe) is None
    assert als_css(eingabe) == ""


def test_kurzschreibweise_wird_verstanden():
    assert palette("#fff")["vereinsfarbe"] == "#ffffff"
    assert palette("abc")["vereinsfarbe"] == "#aabbcc"


def test_als_css_ist_einsetzbar():
    css = als_css("#1769d4")
    assert css.startswith("--vereinsfarbe:#1769d4;")
    assert "--vereinsfarbe-text:#ffffff;" in css
    assert css.endswith(";")
    assert '"' not in css, "darf das style-Attribut nicht sprengen"


# ──────────────────────────────────────
# Taugt die Farbe ueberhaupt als Akzent?
# ──────────────────────────────────────

def test_zu_dunkle_farbe_auf_dunklem_grund_wird_abgelehnt():
    assert taugt_als_akzent("#1a2332", "#111827") is False


def test_kraeftige_farbe_wird_angenommen():
    assert taugt_als_akzent("#22c55e", "#111827") is True
    assert taugt_als_akzent("#ffdd00", "#111827") is True


def test_helle_farbe_auf_hellem_grund_wird_abgelehnt():
    assert taugt_als_akzent("#f8fafc", "#ffffff") is False


def test_unsinnige_eingabe_taugt_nicht():
    assert taugt_als_akzent("blau") is False
    assert taugt_als_akzent(None) is False
