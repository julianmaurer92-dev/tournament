#!/usr/bin/env python
"""Kontrast aller Themes gegen WCAG AA pruefen.

Liest app/static/css/tokens.css, zieht die Farbrollen je Theme und Schema
heraus und rechnet die Kontrastverhaeltnisse der Kombinationen nach, die in
der Oberflaeche tatsaechlich vorkommen.

Pruefregeln (WCAG 2.1 AA):
    normaler Text         >= 4.5:1
    grosse Schrift        >= 3.0:1   (Spielstand, Timer, Ueberschriften)
    Bedienelement-Raender >= 3.0:1

Aufruf:
    python scripts/kontrast_pruefen.py
Rueckgabewert 1, wenn eine Pflichtkombination durchfaellt.
"""
import pathlib
import re
import sys

TOKENS = pathlib.Path(__file__).resolve().parent.parent / "app/static/css/tokens.css"

# (Vordergrund, Hintergrund, Mindestverhaeltnis, Beschreibung)
PFLICHT = [
    ("text",       "flaeche-tief",    4.5, "Fliesstext auf Seitenhintergrund"),
    ("text",       "flaeche",         4.5, "Fliesstext auf Karte"),
    ("text",       "flaeche-erhoben", 4.5, "Fliesstext auf erhobener Flaeche"),
    ("text-leise", "flaeche",         4.5, "Nebentext auf Karte"),
    ("text-leise", "flaeche-tief",    4.5, "Nebentext auf Seitenhintergrund"),
    ("text-still", "flaeche",         3.0, "Hinweistext (nur gross)"),
    ("akzent",     "flaeche",         3.0, "Akzent auf Karte (Rahmen, Icons)"),
    ("akzent",     "flaeche-tief",    3.0, "Akzent auf Seitenhintergrund"),
    ("text-auf-akzent", "akzent",     4.5, "Text auf Akzentflaeche (Knopf)"),
    ("rand-interaktiv", "flaeche",    3.0, "Rahmen von Eingabefeldern"),
]


def hex_zu_rgb(wert):
    wert = wert.strip().lstrip("#")
    if len(wert) == 3:
        wert = "".join(z * 2 for z in wert)
    return tuple(int(wert[i:i + 2], 16) for i in (0, 2, 4))


def leuchtdichte(rgb):
    def kanal(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (kanal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def verhaeltnis(farbe_a, farbe_b):
    la, lb = leuchtdichte(hex_zu_rgb(farbe_a)), leuchtdichte(hex_zu_rgb(farbe_b))
    hell, dunkel = max(la, lb), min(la, lb)
    return (hell + 0.05) / (dunkel + 0.05)


def themes_lesen(css):
    """{(theme, schema): {rolle: hexwert}} – Vorgaben werden vererbt."""
    bloecke = re.findall(
        r'\[data-theme="([a-z]+)"\]\[data-schema="(hell|dunkel)"\]\s*\{([^}]*)\}',
        css)
    vorgabe = {}
    for muster in (r':root,\s*\[data-schema="dunkel"\]\s*\{([^}]*)\}',
                   r'\[data-schema="hell"\]\s*\{([^}]*)\}'):
        treffer = re.search(muster, css)
        if treffer:
            schema = "dunkel" if "dunkel" in muster else "hell"
            vorgabe[schema] = dict(re.findall(r'--([a-z-]+):\s*(#[0-9a-fA-F]{3,8})',
                                              treffer.group(1)))

    ergebnis = {}
    for theme, schema, inhalt in bloecke:
        werte = dict(vorgabe.get("dunkel", {}))
        if schema == "hell":
            werte.update(vorgabe.get("hell", {}))
        werte.update(dict(re.findall(r'--([a-z-]+):\s*(#[0-9a-fA-F]{3,8})', inhalt)))
        # Rollen, die per var(--x) auf eine andere Rolle zeigen, aufloesen
        for rolle, ziel in re.findall(r'--([a-z-]+):\s*var\(--([a-z-]+)\)', css):
            if ziel in werte:
                werte.setdefault(rolle, werte[ziel])
        ergebnis[(theme, schema)] = werte
    return ergebnis


def main():
    css = TOKENS.read_text()
    themes = themes_lesen(css)
    if not themes:
        sys.exit("Keine Themes in tokens.css gefunden.")

    fehler = []
    knapp = []
    print(f"{len(themes)} Theme-Varianten gefunden\n")
    for (theme, schema) in sorted(themes):
        werte = themes[(theme, schema)]
        zeilen = []
        for vorn, hinten, minimum, was in PFLICHT:
            if vorn not in werte or hinten not in werte:
                continue
            v = verhaeltnis(werte[vorn], werte[hinten])
            marke = "ok " if v >= minimum else "FEHLT"
            if v < minimum:
                fehler.append(f"{theme}/{schema}: {was} {v:.2f}:1 (noetig {minimum})")
            elif v < minimum * 1.1:
                knapp.append(f"{theme}/{schema}: {was} {v:.2f}:1")
            zeilen.append(f"    {marke} {v:5.2f}  {was}")
        schlimmstes = min(
            (verhaeltnis(werte[v], werte[h])
             for v, h, _m, _w in PFLICHT if v in werte and h in werte),
            default=0)
        print(f"  {theme:<12} {schema:<7} schlechtester Wert {schlimmstes:.2f}:1")
        if fehler and fehler[-1].startswith(f"{theme}/{schema}"):
            for z in zeilen:
                if "FEHLT" in z:
                    print(z)

    print()
    if knapp:
        print(f"{len(knapp)} knappe Werte (bestanden, aber unter 10 % Reserve):")
        for k in knapp[:10]:
            print("   ", k)
        print()
    if fehler:
        print(f"{len(fehler)} Kombinationen bestehen WCAG AA NICHT:")
        for f in fehler:
            print("   ", f)
        return 1
    print("Alle Pflichtkombinationen bestehen WCAG AA.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
