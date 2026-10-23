"""Auswertungen aus Spielereignissen: Torschuetzen und Fair-Play.

Die Funktionen arbeiten auf einer Liste von Ereignis-Datensaetzen, nicht auf
der Datenbank. So lassen sie sich ohne Turnier und ohne Session testen; die
Routen geben einfach die Ereignisse des Turniers hinein.

Ein Ereignis ist ein dict:
    {"art", "team_id", "team_name", "player_name", "minute"}
"""
from app.models import (
    EREIGNIS_EIGENTOR, EREIGNIS_TOR, FAIRPLAY_PUNKTE, KARTEN_ARTEN,
)


def _name_schluessel(name):
    """Namen zum Zusammenfassen vereinheitlichen.

    "max mustermann", "Max  Mustermann" und " Max Mustermann " sind derselbe
    Spieler. Angezeigt wird trotzdem die erste gefundene Schreibweise.
    """
    return " ".join((name or "").split()).lower()


def torschuetzenliste(ereignisse, mindest_tore=1):
    """Torschuetzen absteigend nach Toren.

    Eigentore zaehlen fuer das gegnerische Team, aber nicht als Treffer des
    Schuetzen – sie tauchen hier also nicht auf. Ereignisse ohne Namen
    werden uebersprungen: "1 Tor von (unbekannt)" ist keine Information,
    die in eine Torschuetzenliste gehoert.
    """
    treffer = {}
    for e in ereignisse:
        if e.get("art") != EREIGNIS_TOR:
            continue
        name = (e.get("player_name") or "").strip()
        if not name:
            continue
        schluessel = (e.get("team_id"), _name_schluessel(name))
        eintrag = treffer.setdefault(schluessel, {
            "player_name": name,
            "team_id": e.get("team_id"),
            "team_name": e.get("team_name"),
            "tore": 0,
        })
        eintrag["tore"] += 1

    liste = [e for e in treffer.values() if e["tore"] >= mindest_tore]
    liste.sort(key=lambda e: (-e["tore"], e["player_name"].lower()))

    # Gleiche Toranzahl = gleicher Platz (1., 2., 2., 4. ...)
    platz = 0
    vorherige_tore = None
    for i, eintrag in enumerate(liste, 1):
        if eintrag["tore"] != vorherige_tore:
            platz = i
            vorherige_tore = eintrag["tore"]
        eintrag["platz"] = platz
    return liste


def tore_ohne_schuetzen(ereignisse):
    """Anzahl Tore, bei denen kein Schuetze eingetragen ist."""
    return sum(1 for e in ereignisse
               if e.get("art") == EREIGNIS_TOR
               and not (e.get("player_name") or "").strip())


def fairplay_tabelle(ereignisse, teams):
    """Fair-Play-Wertung je Team – wenige Strafpunkte sind besser.

    teams: Liste von (team_id, team_name). Teams ohne Karten erscheinen mit
    null Punkten, sonst sieht es aus, als waeren sie nicht angetreten.
    """
    tabelle = {
        team_id: {
            "team_id": team_id, "team_name": team_name,
            "gelb": 0, "gelb_rot": 0, "rot": 0,
            "karten": 0, "strafpunkte": 0,
        }
        for team_id, team_name in teams
    }

    for e in ereignisse:
        art = e.get("art")
        if art not in KARTEN_ARTEN:
            continue
        eintrag = tabelle.get(e.get("team_id"))
        if eintrag is None:
            continue
        eintrag[art] += 1
        eintrag["karten"] += 1
        eintrag["strafpunkte"] += FAIRPLAY_PUNKTE[art]

    liste = sorted(tabelle.values(),
                   key=lambda e: (e["strafpunkte"], e["karten"],
                                  (e["team_name"] or "").lower()))
    platz = 0
    vorherige = None
    for i, eintrag in enumerate(liste, 1):
        schluessel = (eintrag["strafpunkte"], eintrag["karten"])
        if schluessel != vorherige:
            platz = i
            vorherige = schluessel
        eintrag["platz"] = platz
    return liste


def karten_je_spieler(ereignisse):
    """Spieler mit Karten – fuer Sperren und Rueckfragen am Turniertag."""
    spieler = {}
    for e in ereignisse:
        art = e.get("art")
        if art not in KARTEN_ARTEN:
            continue
        name = (e.get("player_name") or "").strip()
        if not name:
            continue
        schluessel = (e.get("team_id"), _name_schluessel(name))
        eintrag = spieler.setdefault(schluessel, {
            "player_name": name,
            "team_id": e.get("team_id"),
            "team_name": e.get("team_name"),
            "gelb": 0, "gelb_rot": 0, "rot": 0, "strafpunkte": 0,
        })
        eintrag[art] += 1
        eintrag["strafpunkte"] += FAIRPLAY_PUNKTE[art]

    liste = list(spieler.values())
    liste.sort(key=lambda e: (-e["strafpunkte"], e["player_name"].lower()))
    return liste


def tore_je_team(ereignisse):
    """Aus Ereignissen gezaehlte Tore je Team.

    Eigentore werden dem gegnerischen Team zugeschlagen – dafuer muss der
    Aufrufer bei Eigentoren bereits das begünstigte Team eintragen, siehe
    app/ereignisse.py. Dient dem Abgleich mit dem eingetragenen Ergebnis.
    """
    zaehler = {}
    for e in ereignisse:
        if e.get("art") not in (EREIGNIS_TOR, EREIGNIS_EIGENTOR):
            continue
        team_id = e.get("team_id")
        zaehler[team_id] = zaehler.get(team_id, 0) + 1
    return zaehler


def ergebnis_stimmt(match_score1, match_score2, team1_id, team2_id,
                    ereignisse):
    """Passt die Summe der Torereignisse zum eingetragenen Ergebnis?

    Liefert (stimmt, tore_team1, tore_team2). Wird im Adminbereich als
    Hinweis angezeigt: Wer Tore nur ueber die Plus-Knoepfe zaehlt und
    Schuetzen nur teilweise eintraegt, soll das sehen und nicht in einer
    falschen Torschuetzenliste suchen.
    """
    zaehler = tore_je_team(ereignisse)
    tore1 = zaehler.get(team1_id, 0)
    tore2 = zaehler.get(team2_id, 0)
    return (tore1 == (match_score1 or 0) and tore2 == (match_score2 or 0),
            tore1, tore2)
