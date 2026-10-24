"""Themes: Katalog, Auflösung und Abbildung der alten Namen.

Vorher gab es zehn Themes als lose `[data-theme="x"]`-Bloecke im CSS, alle
dunkel bis auf eines. Jetzt gibt es zehn Themes mit je einer hellen und
einer dunklen Variante.

Die alten Namen bleiben gueltig: Wer "midnight" gespeichert hat, bekommt
"mitternacht" in dunkel. Niemandem bricht seine Einstellung weg.
"""

# Schluessel -> Anzeige. Die Vorschaufarben stehen hier, damit die Galerie
# sie nicht aus dem CSS parsen muss.
THEMES = {
    "rasen": {
        "name": "Rasen",
        "beschreibung": "Grün wie der Platz. Die Vorgabe.",
        "vorschau": {"dunkel": ("#0a1410", "#162c23", "#34d27b"),
                     "hell":   ("#f1f8f3", "#ffffff", "#0d7c42")},
    },
    "mitternacht": {
        "name": "Mitternacht",
        "beschreibung": "Fast schwarz. Für dunkle Hallen und Abendspiele.",
        "vorschau": {"dunkel": ("#07080c", "#151823", "#7c8cff"),
                     "hell":   ("#f3f4fb", "#ffffff", "#4452d6")},
    },
    "schiefer": {
        "name": "Schiefer",
        "beschreibung": "Neutrales Grau. Hält sich maximal zurück.",
        "vorschau": {"dunkel": ("#0d1117", "#1d242e", "#4c9aff"),
                     "hell":   ("#f4f6f8", "#ffffff", "#1769d4")},
    },
    "ozean": {
        "name": "Ozean",
        "beschreibung": "Kühles Blau mit Türkis-Akzent.",
        "vorschau": {"dunkel": ("#06121f", "#122a42", "#2ec5d8"),
                     "hell":   ("#eff7fc", "#ffffff", "#0b7f91")},
    },
    "ziegel": {
        "name": "Ziegel",
        "beschreibung": "Warmes Rot. Für Vereine in Rot-Weiß.",
        "vorschau": {"dunkel": ("#180b0c", "#31191b", "#ff6b5e"),
                     "hell":   ("#fdf3f2", "#ffffff", "#c23a2b")},
    },
    "forst": {
        "name": "Forst",
        "beschreibung": "Dunkles Tannengrün mit Gold.",
        "vorschau": {"dunkel": ("#081512", "#143029", "#c9a227"),
                     "hell":   ("#f0f7f4", "#ffffff", "#8a6d09")},
    },
    "bernstein": {
        "name": "Bernstein",
        "beschreibung": "Warm und kräftig. Gut bei Sonnenlicht.",
        "vorschau": {"dunkel": ("#16100a", "#2f2416", "#ffb340"),
                     "hell":   ("#fdf6ea", "#ffffff", "#a06a00")},
    },
    "veilchen": {
        "name": "Veilchen",
        "beschreibung": "Kräftiges Lila. Fällt auf.",
        "vorschau": {"dunkel": ("#0f0a1c", "#22183a", "#a78bfa"),
                     "hell":   ("#f6f2fd", "#ffffff", "#6b3fd4")},
    },
    "papier": {
        "name": "Papier",
        "beschreibung": "Sehr hell und ruhig. Für Beamer bei Tageslicht.",
        "vorschau": {"hell":   ("#faf9f7", "#ffffff", "#1f6feb"),
                     "dunkel": ("#16150f", "#2b2820", "#74a9ff")},
    },
    "stadion": {
        "name": "Stadion",
        "beschreibung": "Höchster Kontrast. Für große Entfernung.",
        "vorschau": {"dunkel": ("#000000", "#171717", "#ffdd00"),
                     "hell":   ("#ffffff", "#ffffff", "#0b57d0")},
    },
}

SCHEMATA = ("dunkel", "hell")

STANDARD_THEME = "rasen"
STANDARD_SCHEMA = "dunkel"

# Alte Theme-Namen aus der Datenbank -> (neues Theme, Schema).
# Jeder alte Name behaelt seinen Charakter: midnight war fast schwarz und
# bleibt fast schwarz, light war hell und bleibt hell.
ALTE_NAMEN = {
    "dark":     ("rasen", "dunkel"),      # Vorgabe war dunkel mit Gruen-Akzent
    "midnight": ("mitternacht", "dunkel"),
    "slate":    ("schiefer", "dunkel"),
    "ocean":    ("ozean", "dunkel"),
    "crimson":  ("ziegel", "dunkel"),
    "light":    ("schiefer", "hell"),
    "navy":     ("ozean", "dunkel"),      # Marineblau mit Gold
    "forest":   ("forst", "dunkel"),
    "amber":    ("bernstein", "dunkel"),
    "violet":   ("veilchen", "dunkel"),
}


def aufloesen(gespeichert):
    """Gespeicherten Wert in (theme, schema) uebersetzen.

    Akzeptiert:
      - neue Schreibweise "rasen:hell"
      - neues Theme ohne Schema  -> Standardschema des Themes
      - alte Namen wie "midnight"
      - Unsinn oder leer         -> Vorgabe

    Nie eine Ausnahme: Ein kaputter Wert in der Datenbank darf keine Seite
    weiss machen.
    """
    wert = (gespeichert or "").strip().lower()
    if not wert:
        return STANDARD_THEME, STANDARD_SCHEMA

    if ":" in wert:
        theme, _, schema = wert.partition(":")
        if theme in THEMES and schema in SCHEMATA:
            return theme, schema
        if theme in THEMES:
            return theme, STANDARD_SCHEMA

    if wert in THEMES:
        # Papier ist von Haus aus hell – sonst saehe es aus wie ein Fehler
        return wert, "hell" if wert == "papier" else STANDARD_SCHEMA

    if wert in ALTE_NAMEN:
        return ALTE_NAMEN[wert]

    return STANDARD_THEME, STANDARD_SCHEMA


def speicherwert(theme, schema):
    """(theme, schema) in den Wert fuer die Datenbank."""
    theme = theme if theme in THEMES else STANDARD_THEME
    schema = schema if schema in SCHEMATA else STANDARD_SCHEMA
    return f"{theme}:{schema}"


def katalog():
    """Themes fuer die Galerie, in fester Reihenfolge."""
    return [
        {
            "schluessel": schluessel,
            "name": daten["name"],
            "beschreibung": daten["beschreibung"],
            "vorschau": daten["vorschau"],
        }
        for schluessel, daten in THEMES.items()
    ]
