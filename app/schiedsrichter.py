"""Schiedsrichter auf Spiele verteilen und Konflikte finden.

Reine Logik ohne Datenbank. Die Routen uebergeben Dictionaries.

Spiel:          {"id", "anstoss", "feld", "teams", "schiedsrichter_id"}
Schiedsrichter: {"id", "name", "team_id", "aktiv"}
"""
from collections import defaultdict


def _zeitfenster(spiel):
    """Schluessel, der ein Zeitfenster identifiziert.

    Spiele ohne Anstosszeit koennen nicht auf zeitliche Konflikte geprueft
    werden – sie bekommen je Spiel ein eigenes Fenster, damit die Zuteilung
    trotzdem funktioniert.
    """
    anstoss = spiel.get("anstoss")
    return anstoss if anstoss is not None else ("ohne-zeit", spiel.get("id"))


def _eigenes_team(schiedsrichter, spiel):
    team_id = schiedsrichter.get("team_id")
    if team_id is None:
        return False
    return team_id in (spiel.get("teams") or ())


def verteile_schiedsrichter(spiele, schiedsrichter, nur_leere=True):
    """Schiedsrichter moeglichst gleichmaessig auf Spiele verteilen.

    Regeln, in dieser Reihenfolge:
    1. niemand pfeift zwei Spiele gleichzeitig
    2. niemand pfeift ein Spiel der eigenen Mannschaft
    3. niemand pfeift, wer gerade selbst spielt (Spieler-Schiedsrichter)
    4. wer bisher am wenigsten gepfiffen hat, kommt zuerst

    nur_leere=True laesst bereits zugeteilte Spiele unberuehrt – so kann man
    nachtraeglich auffuellen, ohne eine von Hand gemachte Einteilung zu
    zerstoeren.

    Liefert (zuteilung, offen):
        zuteilung = {spiel_id: schiedsrichter_id}
        offen     = Liste von Spiel-IDs, fuer die niemand passte
    """
    aktive = [s for s in schiedsrichter if s.get("aktiv", True)]
    zuteilung = {}
    offen = []
    if not aktive:
        return zuteilung, [s["id"] for s in spiele
                           if not (nur_leere and s.get("schiedsrichter_id"))]

    einsaetze = defaultdict(int)
    belegt = defaultdict(set)         # Zeitfenster -> {schiedsrichter_id}
    spielt_im_fenster = defaultdict(set)   # Zeitfenster -> {team_id}

    # Bestehende Zuteilungen beruecksichtigen, damit die Last stimmt
    for spiel in spiele:
        fenster = _zeitfenster(spiel)
        for team_id in (spiel.get("teams") or ()):
            if team_id is not None:
                spielt_im_fenster[fenster].add(team_id)
        vorhanden = spiel.get("schiedsrichter_id")
        if vorhanden:
            einsaetze[vorhanden] += 1
            belegt[fenster].add(vorhanden)

    # Nach Anstosszeit abarbeiten; Spiele ohne Zeit zuletzt
    def sortierschluessel(spiel):
        anstoss = spiel.get("anstoss")
        return (anstoss is None, anstoss, spiel.get("feld") or 1,
                spiel.get("id") or 0)

    for spiel in sorted(spiele, key=sortierschluessel):
        if nur_leere and spiel.get("schiedsrichter_id"):
            continue

        fenster = _zeitfenster(spiel)

        def frei(s):
            return s["id"] not in belegt[fenster]

        def spielt_selbst(s):
            """Die eigene Mannschaft spielt im selben Zeitfenster."""
            team_id = s.get("team_id")
            return team_id is not None and team_id in spielt_im_fenster[fenster]

        # Beste Wahl: frei, nicht die eigene Mannschaft, spielt nicht selbst
        kandidaten = [s for s in aktive
                      if frei(s) and not _eigenes_team(s, spiel)
                      and not spielt_selbst(s)]
        if not kandidaten:
            # Erste Lockerung: darf selbst im Zeitfenster spielen (z. B. ein
            # Betreuer, der parallel auf dem anderen Feld dabei ist)
            kandidaten = [s for s in aktive
                          if frei(s) and not _eigenes_team(s, spiel)]
        if not kandidaten:
            # Zweite Lockerung: ein Betreuer der eigenen Mannschaft ist
            # besser als kein Schiedsrichter. Die Konfliktpruefung zeigt es.
            kandidaten = [s for s in aktive if frei(s)]
        if not kandidaten:
            offen.append(spiel["id"])
            continue

        gewaehlt = min(kandidaten,
                       key=lambda s: (einsaetze[s["id"]], s["id"]))
        zuteilung[spiel["id"]] = gewaehlt["id"]
        einsaetze[gewaehlt["id"]] += 1
        belegt[fenster].add(gewaehlt["id"])

    return zuteilung, offen


def finde_schiedsrichter_konflikte(spiele, schiedsrichter):
    """Probleme in einer bestehenden Einteilung als Textliste.

    Leer, wenn alles passt.
    """
    namen = {s["id"]: s.get("name") or f"#{s['id']}" for s in schiedsrichter}
    eigene_teams = {s["id"]: s.get("team_id") for s in schiedsrichter}

    konflikte = []
    nach_fenster = defaultdict(list)
    for spiel in spiele:
        if spiel.get("schiedsrichter_id"):
            nach_fenster[_zeitfenster(spiel)].append(spiel)

    for fenster, gleichzeitig in sorted(
            nach_fenster.items(),
            key=lambda eintrag: str(eintrag[0])):
        gezaehlt = defaultdict(list)
        for spiel in gleichzeitig:
            gezaehlt[spiel["schiedsrichter_id"]].append(spiel)
        for sr_id, liste in gezaehlt.items():
            if len(liste) > 1:
                uhrzeit = (fenster.strftime("%H:%M")
                           if hasattr(fenster, "strftime") else "ohne Zeit")
                nummern = ", ".join(f"#{s.get('nummer', s['id'])}"
                                    for s in liste)
                konflikte.append(
                    f"{uhrzeit}: {namen.get(sr_id, '?')} ist für "
                    f"{len(liste)} Spiele gleichzeitig eingeteilt ({nummern})."
                )

    for spiel in spiele:
        sr_id = spiel.get("schiedsrichter_id")
        if not sr_id:
            continue
        eigenes = eigene_teams.get(sr_id)
        if eigenes is not None and eigenes in (spiel.get("teams") or ()):
            konflikte.append(
                f"Spiel #{spiel.get('nummer', spiel['id'])}: "
                f"{namen.get(sr_id, '?')} pfeift ein Spiel der eigenen "
                f"Mannschaft."
            )

    return konflikte


def einsatzzahlen(spiele, schiedsrichter):
    """Wie oft ist wer eingeteilt? Fuer eine faire Verteilung sichtbar machen."""
    zaehler = {s["id"]: 0 for s in schiedsrichter}
    for spiel in spiele:
        sr_id = spiel.get("schiedsrichter_id")
        if sr_id in zaehler:
            zaehler[sr_id] += 1
    return zaehler
