#!/usr/bin/env python3
"""Rechnet jede Theme-Variante von „Anpfiff" gegen WCAG 2.1 AA nach.

Aufruf:
    python3 scripts/kontrast_anpfiff.py          # Pflichtpaare
    python3 scripts/kontrast_anpfiff.py --alle   # alles, auch Hinweise

Rückgabewert 1, wenn eine Pflichtkombination durchfällt – damit lässt
sich das Skript in eine Prüfkette hängen.

Die Grenzwerte stammen aus WCAG 2.1:
  1.4.3  Fließtext            4,5 : 1
  1.4.3  große Schrift        3,0 : 1  (ab 24 px bzw. 19 px fett)
  1.4.11 Bedienelement-Rand   3,0 : 1
"""
import re
import sys
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "app" / "static" / "css" / "anpfiff.css"

# (Vordergrund, Hintergrund, Mindestwert, Beschreibung)
PFLICHT = [
    ("--ap-schrift-farbe", "--ap-grund",      4.5, "Fließtext auf der Seite"),
    ("--ap-schrift-farbe", "--ap-tafel",      4.5, "Fließtext auf einer Tafel"),
    ("--ap-schrift-farbe", "--ap-tafel-tief", 4.5, "Fließtext in einer Eingabe"),
    ("--ap-leise",         "--ap-tafel",      4.5, "Nebentext auf einer Tafel"),
    ("--ap-leise",         "--ap-grund",      4.5, "Nebentext auf der Seite"),
    ("--ap-still",         "--ap-tafel-kopf", 3.0, "Streifenbeschriftung (groß)"),
    ("--ap-auf-akzent",    "--ap-akzent",     4.5, "Schrift auf der Hauptaktion"),
    ("--ap-akzent",        "--ap-tafel",      3.0, "Akzent als Rand oder Symbol"),
    ("--ap-akzent",        "--ap-grund",      3.0, "Akzent auf der Seite"),
    ("--ap-tor",           "--ap-tafel",      3.0, "Spielstand (sehr groß)"),
    ("--ap-live",          "--ap-tafel",      3.0, "Live-Kennzeichnung"),
    ("--ap-gefahr",        "--ap-tafel",      3.0, "Fehler- und Löschfarbe"),
    ("--ap-warnung",       "--ap-tafel",      3.0, "Warnfarbe"),
    # WCAG 1.4.11 gilt fuer Bedienelemente. Der dekorative Rand einer
    # Tafel faellt nicht darunter - er steht unten unter "Hinweis".
    ("--ap-kante-aktiv",   "--ap-tafel",      3.0, "Rand eines Bedienelements"),
    ("--ap-kante-aktiv",   "--ap-tafel-tief", 3.0, "Rand einer Eingabe"),
    ("--ap-kante-aktiv",   "--ap-grund",      3.0, "Bedienelement auf der Seite"),
]

HINWEIS = [
    ("--ap-kante",  "--ap-tafel", 1.2, "Tafelrand überhaupt sichtbar"),
    ("--ap-still",  "--ap-tafel", 4.5, "Beschriftung in Textgröße"),
    ("--ap-kreide", "--ap-tafel", 1.3, "Trennlinie überhaupt sichtbar"),
]


def werte_lesen(text):
    """Alle Theme-Blöcke als {(theme, schema): {name: wert}}."""
    themes = {}
    muster = re.compile(
        r'\[data-theme="([a-z]+)"\]\[data-schema="([a-z]+)"\][^{]*\{([^}]*)\}', re.S)
    for treffer in muster.finditer(text):
        theme, schema, block = treffer.groups()
        werte = dict(re.findall(r'(--ap-[a-z-]+):\s*([^;]+);', block))
        themes.setdefault((theme, schema), {}).update(
            {k: v.strip() for k, v in werte.items()})
    for werte in themes.values():
        aufloesen(werte)
    return themes


def aufloesen(werte, tiefe=4):
    """var(--x) durch den tatsaechlichen Wert ersetzen.

    Eine Rolle darf auf eine andere zeigen – "--ap-kante-aktiv:
    var(--ap-still)" ist gewollt und spart in jedem Theme eine Zeile.
    Der Pruefer muss den Verweis aber bis zur Farbe verfolgen, sonst
    prueft er die Zeichenkette "var(...)" und meldet alles als fehlend.
    """
    muster = re.compile(r'var\(\s*(--ap-[a-z-]+)\s*(?:,[^)]*)?\)')
    for _ in range(tiefe):
        offen = False
        for name, wert in list(werte.items()):
            treffer = muster.search(wert)
            if not treffer:
                continue
            ziel = werte.get(treffer.group(1))
            if ziel is None:
                continue
            werte[name] = muster.sub(lambda m: werte.get(m.group(1), m.group(0)),
                                     wert, count=1).strip()
            offen = True
        if not offen:
            break


def als_rgb(wert):
    wert = wert.strip()
    if not wert.startswith("#"):
        return None
    h = wert[1:]
    if len(h) == 3:
        h = "".join(z * 2 for z in h)
    if len(h) not in (6, 8):
        return None
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def leuchtdichte(rgb):
    def kanal(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (kanal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def kontrast(a, b):
    la, lb = leuchtdichte(a), leuchtdichte(b)
    hell, dunkel = max(la, lb), min(la, lb)
    return (hell + 0.05) / (dunkel + 0.05)


def main():
    alle = "--alle" in sys.argv
    text = CSS.read_text()
    themes = werte_lesen(text)
    if not themes:
        print("Keine Themes gefunden – stimmt der Pfad?")
        return 1

    pruefungen = PFLICHT + (HINWEIS if alle else [])
    fehler = 0
    geprueft = 0

    for (theme, schema) in sorted(themes):
        werte = themes[(theme, schema)]
        zeilen = []
        schlechtester = (99.0, "")
        for vorn, hinten, grenze, was in pruefungen:
            a, b = als_rgb(werte.get(vorn, "")), als_rgb(werte.get(hinten, ""))
            if a is None or b is None:
                zeilen.append(f"      ?  {was}: {vorn} oder {hinten} fehlt")
                fehler += 1
                continue
            k = kontrast(a, b)
            geprueft += 1
            pflicht = (vorn, hinten, grenze, was) in PFLICHT
            if k < grenze:
                marke = "FEHLER" if pflicht else "Hinweis"
                zeilen.append(f"      {marke}  {was}: {k:.2f} < {grenze}"
                              f"  ({werte[vorn]} auf {werte[hinten]})")
                if pflicht:
                    fehler += 1
            if k < schlechtester[0]:
                schlechtester = (k, was)

        marke = "ok  " if not zeilen else "!!  "
        print(f"{marke}{theme:14s} {schema:7s} "
              f"schlechtester Wert {schlechtester[0]:5.2f}  ({schlechtester[1]})")
        for z in zeilen:
            print(z)

    print(f"\n{len(themes)} Varianten, {geprueft} Kombinationen geprüft.")
    if fehler:
        print(f"{fehler} Verstöße gegen WCAG AA.")
        return 1
    print("Alle Pflichtkombinationen bestehen WCAG AA.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
