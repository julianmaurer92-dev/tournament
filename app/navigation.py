"""Die Bereiche des Adminbereichs – an einer Stelle definiert.

Vorher trug jede Vorlage ihr eigenes Menue im Kopf: die Turnierliste
zeigte "Benutzer · Speisekarte · Export/Import", das Dashboard
"Design · Spielplan · Org · Steuerung", die Spielsteuerung nur
"Ereignisse · Dashboard". Welche Bereiche es ueberhaupt gibt, stand
nirgends vollstaendig.

Hier steht die Liste einmal. Welcher Punkt aktiv ist, entscheidet der
Endpunkt der aktuellen Anfrage – nicht die Vorlage.
"""
from flask import request, url_for


# Woerter, unter denen Leute eine Seite suchen, ohne ihren Namen zu
# kennen. "Wo stelle ich die Spielzeit ein?" fuehrt sonst nirgendwohin,
# weil kein Menuepunkt "Spielzeit" heisst.
STICHWORTE = {
    "Übersicht": "dashboard start heute jetzt laufend",
    "Spielplan": "spiele paarungen zeiten spielfelder anstoss spielzeit "
                 "verlängerung gruppen auslosung drucken",
    "Teams & Gruppen": "mannschaften vereine anmeldungen trikot wappen logo "
                       "spieler kader",
    "Schiedsrichter": "pfeifen einsatzplan unparteiische",
    "Statistik": "torschützen torjäger karten ereignisse tabelle zahlen",
    "Siegerehrung": "pokal urkunden platzierung sieger medaillen",
    "Organisation": "kasse startgeld bezahlt quittung speisekarte getränke "
                    "kabinen kabinenschilder sponsoren",
    "Design": "theme farben aussehen dunkel hell vereinsfarbe darstellung",
    "Alle Turniere": "wechseln anderes turnier neu anlegen jahrgang",
    "Speisekarte": "essen getränke preise kuchen wurst kiosk",
    "Benutzer": "konten passwort rechte zugang anmelden spielleiter",
    "Sicherung": "export import backup datei json wiederherstellen kopie",
}


def _punkt(name, endpunkt, icon, slug=None, zahl=None, passt_auf=()):
    """Ein Navigationspunkt. passt_auf: weitere Endpunkte, die hierher gehoeren."""
    try:
        ziel = url_for(endpunkt, slug=slug) if slug else url_for(endpunkt)
    except Exception:
        return None
    aktiv = request.endpoint == endpunkt or request.endpoint in passt_auf
    return {"name": name, "ziel": ziel, "icon": icon, "aktiv": aktiv, "zahl": zahl}


def navigation(tournament=None, zahlen=None):
    """Navigationspunkte fuer die aktuelle Seite.

    Mit Turnier: die Bereiche dieses Turniers.
    Ohne: die uebergreifenden Seiten.
    """
    zahlen = zahlen or {}
    punkte = []

    if tournament is not None:
        slug = tournament.slug
        punkte = [
            _punkt("Übersicht", "admin.dashboard", "layout-dashboard", slug),
            _punkt("Spielplan", "admin.tournament_admin", "calendar-event", slug,
                   passt_auf=("admin.schedule_print",)),
            _punkt("Teams & Gruppen", "anmeldung_admin.liste", "users-group", slug,
                   zahl=zahlen.get("anmeldungen_offen")),
            # Das Icon-Set hat keine Pfeife; die Eckfahne ist die
            # naechstbeste eindeutige Entsprechung.
            _punkt("Schiedsrichter", "schiedsrichter.uebersicht", "flag-3", slug,
                   passt_auf=("schiedsrichter.einsatzplan",)),
            _punkt("Statistik", "ereignisse_admin.statistik_admin", "chart-bar", slug),
            _punkt("Siegerehrung", "siegerehrung_admin.uebersicht", "certificate", slug,
                   passt_auf=("siegerehrung_admin.urkunden",)),
            _punkt("Organisation", "admin.organisation", "cash-banknote", slug,
                   passt_auf=("admin.cabin_signs",)),
            _punkt("Design", "admin.design", "palette", slug),
        ]
        punkte = [p for p in punkte if p]

    allgemein = [
        _punkt("Alle Turniere", "admin.tournament_list", "trophy"),
        _punkt("Speisekarte", "admin.menu_admin", "clipboard-list"),
        _punkt("Benutzer", "admin.user_list", "users-group"),
        _punkt("Sicherung", "admin.export_import_page", "download"),
    ]
    allgemein = [p for p in allgemein if p]
    return punkte + allgemein


def palette_eintraege(tournament=None, teams=(), spiele=(), themes=()):
    """Eintraege fuer die Befehlspalette (Strg/Cmd+K).

    Seiten, Teams, Spiele und Themes als eine durchsuchbare Liste.
    Bewusst flach: Wer sucht, will tippen und Enter druecken, nicht
    durch Kategorien navigieren.
    """
    eintraege = []

    for punkt in navigation(tournament):
        eintraege.append({
            "art": "Seite", "name": punkt["name"],
            "ziel": punkt["ziel"], "icon": punkt["icon"],
            "stichwort": STICHWORTE.get(punkt["name"], ""),
        })

    if tournament is not None:
        slug = tournament.slug
        extra = [
            ("Spielplan drucken", "admin.schedule_print", "printer", "papier aushang"),
            ("Kabinenschilder drucken", "admin.cabin_signs", "printer", "umkleide tür"),
            ("Urkunden drucken", "siegerehrung_admin.urkunden", "certificate",
             "diplom siegerehrung"),
            ("Live-Ansicht öffnen", "main.tournament_view", "world",
             "öffentlich website zuschauer"),
            ("Beamer-Ansicht öffnen", "main.tournament_tv", "device-tv",
             "fernseher präsentieren großbild anzeigetafel"),
            ("Handy-Ansicht öffnen", "main.tournament_phone", "device-mobile",
             "smartphone mobil eltern"),
            ("Anmeldeformular öffnen", "anmeldung.anmeldeformular", "user-plus",
             "melden teilnahme vereine einladen"),
        ]
        for name, endpunkt, icon, stichwort in extra:
            try:
                eintraege.append({
                    "art": "Aktion", "name": name,
                    "ziel": url_for(endpunkt, slug=slug), "icon": icon,
                    "stichwort": stichwort,
                })
            except Exception:
                pass

        for team in teams:
            eintraege.append({
                "art": "Mannschaft", "name": team.name,
                "ziel": url_for("admin.tournament_admin", slug=slug) + "#teams",
                "icon": "users-group", "stichwort": "mannschaft verein team",
            })

        for spiel in spiele:
            t1 = spiel.team1.name if spiel.team1 else "?"
            t2 = spiel.team2.name if spiel.team2 else "?"
            zeit = spiel.scheduled_time.strftime("%H:%M") if spiel.scheduled_time else ""
            eintraege.append({
                "art": "Spiel",
                "name": f"{t1} – {t2}" + (f" ({zeit})" if zeit else ""),
                "ziel": url_for("admin.match_control", slug=slug, mid=spiel.id),
                "icon": "player-play",
                # Wer die Steuerung sucht, tippt selten die Mannschaftsnamen
                "stichwort": "spielsteuerung steuerung anpfeifen tor ergebnis "
                             "spielstand uhr " + f"{t1} {t2}".lower(),
            })

        for schluessel, name in themes:
            eintraege.append({
                "art": "Theme", "name": name,
                "ziel": url_for("admin.design", slug=slug) + "?theme=" + schluessel,
                "icon": "palette", "stichwort": "theme farben design aussehen",
            })

    return eintraege
