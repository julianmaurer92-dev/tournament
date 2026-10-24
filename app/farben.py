"""Vereinsfarbe zu einer stimmigen, lesbaren Palette ausbauen.

Der Veranstalter gibt eine Primaerfarbe an (oder uebernimmt sie aus dem
Vereinswappen). Daraus leiten wir ab, was die Oberflaeche braucht:

    --vereinsfarbe        die Farbe selbst
    --vereinsfarbe-hell   fuer Hover
    --vereinsfarbe-leise  flaechige Hinterlegung
    --vereinsfarbe-rand   Fokusring
    --vereinsfarbe-text   Schwarz oder Weiss – je nachdem, was auf der
                          Farbe lesbar ist

Der letzte Punkt ist der wichtige: Eine knallgelbe Vereinsfarbe mit weisser
Schrift ist unlesbar. Die Entscheidung trifft der Kontrast, nicht das Gefuehl.

Reine Rechnerei, keine Datenbank – deshalb einzeln testbar.
"""
import re

_HEX = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _als_rgb(hexwert):
    treffer = _HEX.match((hexwert or "").strip())
    if not treffer:
        return None
    wert = treffer.group(1)
    if len(wert) == 3:
        wert = "".join(z * 2 for z in wert)
    return tuple(int(wert[i:i + 2], 16) for i in (0, 2, 4))


def _als_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(k))) for k in rgb)


def leuchtdichte(rgb):
    """Relative Leuchtdichte nach WCAG."""
    def kanal(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (kanal(k) for k in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def kontrast(rgb_a, rgb_b):
    la, lb = leuchtdichte(rgb_a), leuchtdichte(rgb_b)
    hell, dunkel = max(la, lb), min(la, lb)
    return (hell + 0.05) / (dunkel + 0.05)


# Die beiden Schriftfarben, die wir tatsaechlich verwenden. Kein reines
# Schwarz: #111111 wirkt auf farbigen Flaechen weicher und ist auf Bildschirmen
# angenehmer. Der Vergleich muss gegen genau diese Werte laufen – gegen reines
# Schwarz zu rechnen und dann #111111 auszuliefern, waehlt in Grenzfaellen die
# schlechtere Farbe (z. B. #996699: 4.24:1 statt moeglicher 4.45:1).
SCHRIFT_HELL = "#ffffff"
SCHRIFT_DUNKEL = "#111111"


def lesbare_schrift(hexwert):
    """Helle oder dunkle Schrift – was auf dieser Farbe besser lesbar ist."""
    rgb = _als_rgb(hexwert)
    if rgb is None:
        return SCHRIFT_HELL
    auf_hell = kontrast(rgb, _als_rgb(SCHRIFT_HELL))
    auf_dunkel = kontrast(rgb, _als_rgb(SCHRIFT_DUNKEL))
    return SCHRIFT_HELL if auf_hell >= auf_dunkel else SCHRIFT_DUNKEL


def _aufhellen(rgb, anteil):
    return tuple(k + (255 - k) * anteil for k in rgb)


def _abdunkeln(rgb, anteil):
    return tuple(k * (1 - anteil) for k in rgb)


def palette(hexwert, schema="dunkel"):
    """Vollstaendige Palette zu einer Vereinsfarbe.

    schema: "hell" oder "dunkel" – entscheidet, ob der Hover-Ton heller
    oder dunkler wird, damit er sich vom Untergrund abhebt.

    Liefert None, wenn die Eingabe keine Farbe ist. Die Oberflaeche
    bleibt dann beim Theme-Akzent, statt irgendetwas zu raten.
    """
    rgb = _als_rgb(hexwert)
    if rgb is None:
        return None

    hover = _aufhellen(rgb, 0.18) if schema == "dunkel" else _abdunkeln(rgb, 0.16)
    r, g, b = (round(k) for k in rgb)
    return {
        "vereinsfarbe": _als_hex(rgb),
        "vereinsfarbe-hell": _als_hex(hover),
        "vereinsfarbe-leise": f"rgba({r}, {g}, {b}, 0.15)",
        "vereinsfarbe-rand": f"rgba({r}, {g}, {b}, 0.42)",
        "vereinsfarbe-text": lesbare_schrift(hexwert),
    }


def als_css(hexwert, schema="dunkel"):
    """Palette als CSS-Deklarationen fuer ein style-Attribut."""
    werte = palette(hexwert, schema)
    if not werte:
        return ""
    return "".join(f"--{name}:{wert};" for name, wert in werte.items())


def taugt_als_akzent(hexwert, flaeche="#111827"):
    """Hebt sich die Farbe ueberhaupt genug von der Flaeche ab?

    Unter 3:1 verschwindet ein Akzent auf dem Hintergrund – dann ist es
    ehrlicher, den Theme-Akzent zu behalten und das im Adminbereich zu
    sagen, als eine unsichtbare Farbe zu verwenden.
    """
    rgb, grund = _als_rgb(hexwert), _als_rgb(flaeche)
    if rgb is None or grund is None:
        return False
    return kontrast(rgb, grund) >= 3.0
