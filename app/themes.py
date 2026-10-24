"""Themes: Katalog, Aufloesung und Abbildung alter Namen.

Die Gestaltungssprache heisst „Anpfiff" und bringt acht eigene Themes
mit, jedes hell und dunkel, dazu „Anzeigetafel" fuer den Beamer.

Zwei Generationen alter Namen bleiben gueltig:
  - die urspruenglichen englischen (dark, midnight, slate, ocean,
    crimson, light, navy, forest, amber, violet)
  - die deutschen aus der UX-Nachtschicht (rasen, mitternacht,
    schiefer, ozean, ziegel, forst, bernstein, veilchen, papier,
    stadion)

Niemandem bricht seine Einstellung weg.
"""

# Schluessel -> Anzeige. Die Vorschaufarben stehen hier, damit die
# Galerie sie nicht aus dem CSS parsen muss. Reihenfolge der Werte:
# (Grund, Tafel, Akzent).
THEMES = {
    "rasen": {
        "name": "Rasen",
        "beschreibung": "Platzgruen auf warmem Papier. Die Vorgabe.",
        "vorschau": {"hell":   ("#f4f2ea", "#ffffff", "#11703f"),
                     "dunkel": ("#0a1410", "#12211a", "#43d98a")},
    },
    "flutlicht": {
        "name": "Flutlicht",
        "beschreibung": "Kuehles Blauweiss, dunkel mit Signalgelb.",
        "vorschau": {"hell":   ("#eef2f7", "#ffffff", "#0b5fbe"),
                     "dunkel": ("#070c14", "#101a28", "#d6f94a")},
    },
    "trikot": {
        "name": "Trikot",
        "beschreibung": "Vereinsrot, kraeftig und laut.",
        "vorschau": {"hell":   ("#f7f1f0", "#ffffff", "#ab1f28"),
                     "dunkel": ("#140a0a", "#211312", "#ff6b6b")},
    },
    "auswaerts": {
        "name": "Auswaerts",
        "beschreibung": "Tiefes Blau. Ruhig und seriös.",
        "vorschau": {"hell":   ("#eef0f6", "#ffffff", "#2f3b8f"),
                     "dunkel": ("#080a16", "#121631", "#8ea2ff")},
    },
    "bernstein": {
        "name": "Bernstein",
        "beschreibung": "Warmes Orange auf Sand. Gut bei Sonne.",
        "vorschau": {"hell":   ("#f8f1e4", "#fffdf8", "#9a5410"),
                     "dunkel": ("#140e06", "#221809", "#ffa733")},
    },
    "kreide": {
        "name": "Kreide",
        "beschreibung": "Fast farblos. Laesst die Vereinsfarben sprechen.",
        "vorschau": {"hell":   ("#f2f2f1", "#ffffff", "#2e2e2b"),
                     "dunkel": ("#0f0f0e", "#1a1a18", "#ededea")},
    },
    "vereinsheim": {
        "name": "Vereinsheim",
        "beschreibung": "Holz und Creme. Gemuetlich wie der Tresen.",
        "vorschau": {"hell":   ("#f4eee6", "#fffaf4", "#7a4a21"),
                     "dunkel": ("#15100b", "#221a12", "#e3a765")},
    },
    "nachtspiel": {
        "name": "Nachtspiel",
        "beschreibung": "Beinahe schwarz mit Neongruen. Hoher Kontrast.",
        "vorschau": {"hell":   ("#f0f3ee", "#ffffff", "#2d6b1f"),
                     "dunkel": ("#000000", "#0d0f0d", "#5dff9b")},
    },
    "anzeigetafel": {
        "name": "Anzeigetafel",
        "beschreibung": "Nur dunkel. Fuer den Beamer, aus zehn Metern lesbar.",
        "vorschau": {"hell":   ("#000000", "#0a0a0a", "#ffe600"),
                     "dunkel": ("#000000", "#0a0a0a", "#ffe600")},
    },
}

SCHEMATA = ("dunkel", "hell")

STANDARD_THEME = "rasen"
STANDARD_SCHEMA = "hell"

# „Anzeigetafel" hat keine helle Variante – sie hat genau eine Aufgabe.
NUR_DUNKEL = ("anzeigetafel",)

# Beide Generationen alter Namen. Links steht, was gespeichert sein
# kann; rechts, was es heute bedeutet.
ALTE_NAMEN = {
    # Erste Generation (englisch)
    "dark":        ("rasen", "dunkel"),
    "midnight":    ("nachtspiel", "dunkel"),
    "slate":       ("kreide", "dunkel"),
    "ocean":       ("auswaerts", "dunkel"),
    "crimson":     ("trikot", "dunkel"),
    "light":       ("kreide", "hell"),
    "navy":        ("auswaerts", "dunkel"),
    "forest":      ("rasen", "dunkel"),
    "amber":       ("bernstein", "dunkel"),
    "violet":      ("auswaerts", "dunkel"),
    # Zweite Generation (deutsch, aus der UX-Nachtschicht)
    "mitternacht": ("nachtspiel", "dunkel"),
    "schiefer":    ("kreide", "dunkel"),
    "ozean":       ("auswaerts", "dunkel"),
    "ziegel":      ("trikot", "dunkel"),
    "forst":       ("rasen", "dunkel"),
    "veilchen":    ("auswaerts", "dunkel"),
    "papier":      ("kreide", "hell"),
    "stadion":     ("anzeigetafel", "dunkel"),
}


def aufloesen(gespeichert):
    """Gespeicherten Wert in (theme, schema) uebersetzen.

    Akzeptiert:
      - neue Schreibweise "rasen:hell"
      - neues Theme ohne Schema  -> Standardschema des Themes
      - alte Namen beider Generationen
      - alles andere             -> Vorgabe

    Wirft nie – eine kaputte Einstellung darf keine Seite zerlegen.
    """
    wert = (gespeichert or "").strip().lower()
    if not wert:
        return STANDARD_THEME, STANDARD_SCHEMA

    if ":" in wert:
        theme, _, schema = wert.partition(":")
        if theme in THEMES:
            if theme in NUR_DUNKEL:
                return theme, "dunkel"
            if schema in SCHEMATA:
                return theme, schema
            return theme, STANDARD_SCHEMA
        return STANDARD_THEME, STANDARD_SCHEMA

    if wert in THEMES:
        return wert, "dunkel" if wert in NUR_DUNKEL else STANDARD_SCHEMA

    if wert in ALTE_NAMEN:
        return ALTE_NAMEN[wert]

    return STANDARD_THEME, STANDARD_SCHEMA


def speicherwert(theme, schema):
    """Aus (theme, schema) den Wert machen, der in die Datenbank geht."""
    theme = theme if theme in THEMES else STANDARD_THEME
    schema = schema if schema in SCHEMATA else STANDARD_SCHEMA
    if theme in NUR_DUNKEL:
        schema = "dunkel"
    return f"{theme}:{schema}"


def katalog():
    """Themes fuer die Galerie, in fester Reihenfolge."""
    return [
        {
            "schluessel": schluessel,
            "name": daten["name"],
            "beschreibung": daten["beschreibung"],
            "vorschau": daten["vorschau"],
            "nur_dunkel": schluessel in NUR_DUNKEL,
        }
        for schluessel, daten in THEMES.items()
    ]
