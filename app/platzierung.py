"""Endplatzierung eines Turniers berechnen.

Bisher gab es Platz 1 bis 3 nur als Podium im JavaScript der Live-Ansicht.
Fuer die Siegerehrung braucht man die vollstaendige Liste – und zwar
serverseitig, damit sie sich drucken, exportieren und auf Urkunden setzen
laesst.

Verfahren
---------
Jedes Team bekommt einen Sortierschluessel aus vier Kategorien. Daraus
entsteht eine lueckenlose Rangfolge, die auch fuer ein noch laufendes
Turnier sinnvoll ist:

0. Platz steht fest       – aus Finale, "Spiel um Platz N" oder dem Spiel
                            um Platz 3
1. noch im Rennen         – in der Finalrunde dabei, noch nicht
                            ausgeschieden; Reihenfolge nach Gruppenphase
2. ausgeschieden          – Verlierer einer KO-Runde. Spaetere Runden
                            (Halbfinale) stehen vor fruehereren
                            (Viertelfinale); innerhalb einer Runde wird der
                            Platz geteilt, solange kein Entscheidungsspiel
                            stattgefunden hat
3. Gruppenphase           – nicht in der Finalrunde dabei

Unterstuetzt damit alle Finalformen der App: keine Finalrunde, direktes
Finale, Halbfinale + Finale (mit und ohne Spiel um Platz 3), klassische
KO-Runde und Platzierungsspiele ("rank_vs_rank").

Reine Funktionen, keine Datenbank: die Routen uebergeben Dictionaries.
"""
import re

_PLATZ_RE = re.compile(r"platz\s*(\d+)", re.IGNORECASE)

# Kategorien (kleiner ist besser)
_FEST = 0
_IM_RENNEN = 1
_AUSGESCHIEDEN = 2
_GRUPPENPHASE = 3


def _sieger_verlierer(spiel):
    """(sieger_id, verlierer_id) eines beendeten Spiels, sonst (None, None)."""
    if spiel.get("status") != "finished":
        return None, None
    t1, t2 = spiel.get("team1_id"), spiel.get("team2_id")
    if not t1 or not t2:
        return None, None
    s1 = spiel.get("score_team1") or 0
    s2 = spiel.get("score_team2") or 0
    if s1 > s2:
        return t1, t2
    if s2 > s1:
        return t2, t1
    return None, None          # unentschieden entscheidet nichts


def platz_aus_bezeichnung(label):
    """Zielplatz aus der Spielbezeichnung.

    "Spiel um Platz 5" -> 5, "Finale" -> 1, "Halbfinale 1" -> None.
    "Halbfinale" enthaelt das Wort "finale" – deshalb werden Vor-, Achtel-,
    Viertel- und Halbfinale ausdruecklich ausgenommen.
    """
    if not label:
        return None
    klein = label.lower()
    treffer = _PLATZ_RE.search(klein)
    if treffer:
        return int(treffer.group(1))
    if "finale" in klein and not any(
            wort in klein for wort in ("halbfinale", "viertelfinale",
                                       "achtelfinale", "vorfinale")):
        return 1
    return None


def endplatzierung(final_matches, gesamtrangliste, team_namen=None):
    """Vollstaendige Endplatzierung.

    final_matches:    Liste von dicts mit team1_id, team2_id, score_team1,
                      score_team2, status, final_round, final_label,
                      is_loser_match
    gesamtrangliste:  Ergebnis von calculate_overall_rankings(), also Liste
                      von dicts mit ["team"]["id"] und ["team"]["name"]
    team_namen:       optional {team_id: name} als Rueckfall fuer Teams, die
                      nicht in der Gruppenrangliste stehen

    Liefert eine nach Platz sortierte Liste von dicts:
        {"platz", "team_id", "team_name", "geteilt", "quelle"}
    "geteilt" ist True, wenn mehrere Teams denselben Platz belegen, weil
    kein Entscheidungsspiel stattgefunden hat.
    """
    namen = dict(team_namen or {})
    gruppenrang = {}
    for i, eintrag in enumerate(gesamtrangliste):
        team = eintrag.get("team") or {}
        tid = team.get("id")
        if tid is None:
            continue
        gruppenrang.setdefault(tid, i)
        namen.setdefault(tid, team.get("name"))

    # ── Wer war in der Finalrunde dabei, wer ist ausgeschieden? ──
    teilnehmer = set()
    for spiel in final_matches:
        for tid in (spiel.get("team1_id"), spiel.get("team2_id")):
            if tid:
                teilnehmer.add(tid)
                namen.setdefault(tid, None)

    fest = {}                 # team_id -> Platz
    quelle = {}               # team_id -> Herkunftstext
    ausgeschieden = {}        # team_id -> KO-Runde

    def setze_fest(platz, team_id, herkunft):
        if team_id is None or team_id in fest:
            return
        fest[team_id] = platz
        quelle[team_id] = herkunft

    beendet = [m for m in final_matches if m.get("status") == "finished"]

    # 1) Entscheidungsspiele mit Platzangabe – die aussagekraeftigste Quelle
    for spiel in sorted(beendet,
                        key=lambda m: platz_aus_bezeichnung(
                            m.get("final_label")) or 999):
        platz = platz_aus_bezeichnung(spiel.get("final_label"))
        if platz is None:
            continue
        sieger, verlierer = _sieger_verlierer(spiel)
        if sieger:
            bezeichnung = spiel.get("final_label") or "Entscheidungsspiel"
            setze_fest(platz, sieger, bezeichnung)
            setze_fest(platz + 1, verlierer, bezeichnung)

    # 2) Finale und Spiel um Platz 3 im klassischen Baum
    finale = next((m for m in beendet
                   if m.get("final_round") == 1
                   and not m.get("is_loser_match")), None)
    if finale:
        sieger, verlierer = _sieger_verlierer(finale)
        setze_fest(1, sieger, "Finale")
        setze_fest(2, verlierer, "Finale")

    platz3 = next((m for m in beendet if m.get("is_loser_match")), None)
    if platz3:
        sieger, verlierer = _sieger_verlierer(platz3)
        setze_fest(3, sieger, "Spiel um Platz 3")
        setze_fest(4, verlierer, "Spiel um Platz 3")

    # 3) Verlierer der KO-Runden merken (nur, wenn nicht schon fest)
    for spiel in beendet:
        if spiel.get("is_loser_match"):
            continue
        runde = spiel.get("final_round")
        if not runde:
            continue
        _sieger, verlierer = _sieger_verlierer(spiel)
        if verlierer is None or verlierer in fest:
            continue
        # Spaeteste Runde gewinnt: wer im Halbfinale verliert, wird nicht
        # durch eine frueher verlorene Partie schlechter gestellt.
        vorhanden = ausgeschieden.get(verlierer)
        if vorhanden is None or runde < vorhanden:
            ausgeschieden[verlierer] = runde

    # ── Sortierschluessel je Team ──
    alle_teams = set(namen) | set(gruppenrang) | teilnehmer

    def schluessel(tid):
        if tid in fest:
            return (_FEST, fest[tid], 0, gruppenrang.get(tid, 9999))
        if tid in ausgeschieden:
            return (_AUSGESCHIEDEN, ausgeschieden[tid], 0,
                    gruppenrang.get(tid, 9999))
        if tid in teilnehmer:
            return (_IM_RENNEN, 0, 0, gruppenrang.get(tid, 9999))
        return (_GRUPPENPHASE, 0, 0, gruppenrang.get(tid, 9999))

    sortiert = sorted(alle_teams, key=schluessel)

    # ── Plaetze vergeben, Gleichstaende zusammenfassen ──
    def gruppierschluessel(tid):
        """Teams mit gleichem Schluessel teilen sich einen Platz.

        Geteilt wird nur, wenn kein Entscheidungsspiel stattgefunden hat,
        also innerhalb einer KO-Runde. Noch laufende und nicht
        qualifizierte Teams werden nach Gruppenphase durchnummeriert.
        """
        if tid in ausgeschieden:
            return (_AUSGESCHIEDEN, ausgeschieden[tid])
        if tid in fest:
            return (_FEST, fest[tid], tid)
        return (None, tid)

    ergebnis = []
    platz = 1
    i = 0
    while i < len(sortiert):
        aktueller = gruppierschluessel(sortiert[i])
        block = [sortiert[i]]
        j = i + 1
        while j < len(sortiert) and gruppierschluessel(sortiert[j]) == aktueller:
            block.append(sortiert[j])
            j += 1

        geteilt = len(block) > 1
        for tid in block:
            if tid in fest:
                herkunft = quelle.get(tid, "")
            elif tid in ausgeschieden:
                runde = ausgeschieden[tid]
                herkunft = f"ausgeschieden: {_rundenname(runde)}"
            elif tid in teilnehmer:
                herkunft = "noch im Rennen"
            else:
                herkunft = "Gruppenphase"
            ergebnis.append({
                "platz": platz,
                "team_id": tid,
                "team_name": namen.get(tid),
                "geteilt": geteilt,
                "quelle": herkunft,
            })
        platz += len(block)
        i = j

    return ergebnis


def _rundenname(runde):
    return {1: "Finalrunde", 2: "Halbfinale", 3: "Viertelfinale",
            4: "Achtelfinale"}.get(runde, f"Runde {runde}")


def medaille(platz):
    """Symbol fuer die ersten drei Plaetze."""
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(platz, "")


def siegerehrung_ablauf(platzierung):
    """Aufrufreihenfolge fuer die Siegerehrung: von hinten nach vorne.

    So macht man es auf dem Platz – der Sieger kommt zuletzt. Liefert die
    Platzierung in umgekehrter Reihenfolge, mit Medaillen fuer die ersten
    drei.
    """
    umgekehrt = sorted(platzierung, key=lambda e: (-e["platz"],
                                                   e["team_name"] or ""))
    return [dict(e, medaille=medaille(e["platz"])) for e in umgekehrt]
