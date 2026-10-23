"""Spielplanung: Begegnungen auf Zeitfenster und Spielfelder verteilen.

Bewusst ohne Datenbank und ohne Flask – reine Funktionen, die sich einzeln
testen lassen. Der Aufrufer (app/admin.py) uebersetzt das Ergebnis in
Match-Objekte.

Begriffe
--------
Begegnung  Paarung zweier Teams, z. B. (12, 7, gruppe_id)
Slot       Zeitfenster, in dem auf allen Feldern gleichzeitig gespielt wird
Feld       Spielfeld 1..n innerhalb eines Slots
"""
from datetime import datetime, timedelta
from itertools import combinations


class Begegnung:
    """Eine geplante Paarung. Leichtgewichtig, damit Tests lesbar bleiben."""

    __slots__ = ("team1", "team2", "gruppe", "nummer")

    def __init__(self, team1, team2, gruppe=None, nummer=0):
        self.team1 = team1
        self.team2 = team2
        self.gruppe = gruppe
        self.nummer = nummer

    @property
    def teams(self):
        return (self.team1, self.team2)

    def __repr__(self):                     # pragma: no cover - nur Debugging
        return f"Begegnung({self.team1} vs {self.team2}, Gruppe {self.gruppe})"

    def __eq__(self, other):
        return (isinstance(other, Begegnung)
                and self.team1 == other.team1
                and self.team2 == other.team2
                and self.gruppe == other.gruppe)

    def __hash__(self):
        return hash((self.team1, self.team2, self.gruppe))


def jeder_gegen_jeden(team_ids, gruppe=None):
    """Alle Paarungen innerhalb einer Gruppe."""
    return [Begegnung(a, b, gruppe) for a, b in combinations(team_ids, 2)]


def begegnungen_fuer_gruppen(gruppen):
    """gruppen: Liste von (gruppen_id, [team_ids]) -> Liste von Begegnungen."""
    alle = []
    for gruppen_id, team_ids in gruppen:
        if len(team_ids) >= 2:
            alle.extend(jeder_gegen_jeden(team_ids, gruppen_id))
    return alle


# ──────────────────────────────────────
# Verteilung auf Slots und Felder
# ──────────────────────────────────────

def _ruhe(begegnung, zuletzt_gespielt, slot):
    """Wie viele Slots hat das knappere der beiden Teams pausiert?

    Ein Team, das noch nie gespielt hat, bekommt einen sehr hohen Wert –
    es soll zuerst drankommen.
    """
    werte = []
    for team in begegnung.teams:
        letzter = zuletzt_gespielt.get(team)
        werte.append(10_000 if letzter is None else slot - letzter)
    return min(werte)


def plane_slots(begegnungen, felder=1, mindestpause=1):
    """Begegnungen auf Slots und Felder verteilen.

    Harte Regel: Kein Team spielt zweimal im selben Slot. Das klingt
    selbstverstaendlich, war es aber nicht – der bisherige Generator hat die
    Spiele nur zufaellig gemischt und konnte dieselbe Mannschaft zeitgleich
    auf Feld 1 und Feld 2 ansetzen.

    Weiche Regel: Zwischen zwei Spielen einer Mannschaft sollen mindestens
    `mindestpause` Slots liegen. Laesst sich das nicht einhalten (z. B. vier
    Teams auf zwei Feldern), wird die Regel gelockert statt zu scheitern.

    Liefert eine Liste von Slots; jeder Slot ist eine Liste von
    (feld_nummer, Begegnung), aufsteigend nach Feld.
    """
    if felder < 1:
        raise ValueError("Es braucht mindestens ein Spielfeld.")

    verbleibend = list(begegnungen)
    zuletzt_gespielt = {}
    slots = []
    slot_index = 0

    while verbleibend:
        belegt = set()
        slot = []

        while len(slot) < felder:
            kandidat = _naechster_kandidat(
                verbleibend, belegt, zuletzt_gespielt, slot_index, mindestpause)
            if kandidat is None:
                break
            verbleibend.remove(kandidat)
            belegt.update(kandidat.teams)
            slot.append((len(slot) + 1, kandidat))

        if not slot:
            # Kann nur passieren, wenn verbleibend leer ist – zur Sicherheit
            break   # pragma: no cover

        for _feld, begegnung in slot:
            for team in begegnung.teams:
                zuletzt_gespielt[team] = slot_index

        slots.append(slot)
        slot_index += 1

    return slots


def _naechster_kandidat(verbleibend, belegt, zuletzt_gespielt, slot, mindestpause):
    """Beste noch passende Begegnung fuer diesen Slot – oder None."""
    frei = [b for b in verbleibend if not (set(b.teams) & belegt)]
    if not frei:
        return None

    # Erst versuchen, die Mindestpause einzuhalten ...
    ausgeruht = [b for b in frei if _ruhe(b, zuletzt_gespielt, slot) >= mindestpause]
    auswahl = ausgeruht or frei

    # ... dann das Team bevorzugen, das am laengsten nicht gespielt hat.
    # Bei Gleichstand entscheidet die urspruengliche Reihenfolge, damit das
    # Ergebnis reproduzierbar bleibt.
    return max(auswahl, key=lambda b: (_ruhe(b, zuletzt_gespielt, slot), -b.nummer))


# ──────────────────────────────────────
# Anstosszeiten
# ──────────────────────────────────────

def slot_zeiten(anzahl_slots, start, spielzeit_min, pause_min=5,
                lange_pause_nach=None, lange_pause_min=0):
    """Anstosszeit je Slot berechnen.

    start:              datetime des ersten Anstosses
    spielzeit_min:      Netto-Spielzeit einer Partie
    pause_min:          Wechselzeit zwischen zwei Slots
    lange_pause_nach:   nach diesem Slot (1-basiert) eine laengere Pause
    lange_pause_min:    Laenge dieser Pause in Minuten (zusaetzlich)
    """
    if spielzeit_min <= 0:
        raise ValueError("Die Spielzeit muss groesser als null sein.")
    if pause_min < 0:
        raise ValueError("Die Pause darf nicht negativ sein.")

    zeiten = []
    zeitpunkt = start
    for i in range(anzahl_slots):
        zeiten.append(zeitpunkt)
        zeitpunkt = zeitpunkt + timedelta(minutes=spielzeit_min + pause_min)
        if lange_pause_nach and lange_pause_min and (i + 1) == lange_pause_nach:
            zeitpunkt = zeitpunkt + timedelta(minutes=lange_pause_min)
    return zeiten


def erstelle_spielplan(begegnungen, felder=1, mindestpause=1, start=None,
                       spielzeit_min=10, pause_min=5,
                       lange_pause_nach=None, lange_pause_min=0,
                       startnummer=1):
    """Kompletter Spielplan: Slots, Felder und Anstosszeiten in einem Schritt.

    Liefert eine Liste von dicts:
        {"nummer", "slot", "feld", "anstoss", "begegnung"}
    "nummer" ist die fortlaufende Spielnummer (match_order), die Spiele sind
    nach Anstosszeit und dann nach Feld sortiert.
    """
    slots = plane_slots(begegnungen, felder=felder, mindestpause=mindestpause)
    zeiten = slot_zeiten(
        len(slots), start or datetime(2000, 1, 1, 9, 0),
        spielzeit_min=spielzeit_min, pause_min=pause_min,
        lange_pause_nach=lange_pause_nach, lange_pause_min=lange_pause_min,
    ) if slots else []

    plan = []
    nummer = startnummer
    for slot_index, slot in enumerate(slots):
        for feld, begegnung in slot:
            plan.append({
                "nummer": nummer,
                "slot": slot_index + 1,
                "feld": feld,
                "anstoss": zeiten[slot_index] if start else None,
                "begegnung": begegnung,
            })
            nummer += 1
    return plan


# ──────────────────────────────────────
# Pruefung bestehender Spielplaene
# ──────────────────────────────────────

def finde_konflikte(spiele):
    """Doppelbelegungen in einem bestehenden Spielplan finden.

    spiele: Liste von dicts mit "nummer", "anstoss", "feld", "teams"
            (teams = Tupel/Liste der beteiligten Team-IDs, None erlaubt)

    Liefert eine Liste von Textmeldungen – leer, wenn alles sauber ist.
    Hilft bei von Hand gebauten oder importierten Spielplaenen.
    """
    konflikte = []
    nach_zeit = {}
    for spiel in spiele:
        if not spiel.get("anstoss"):
            continue
        nach_zeit.setdefault(spiel["anstoss"], []).append(spiel)

    for anstoss, gleichzeitig in sorted(nach_zeit.items()):
        uhrzeit = anstoss.strftime("%H:%M")

        # Zwei Spiele auf demselben Feld zur selben Zeit
        felder = {}
        for spiel in gleichzeitig:
            felder.setdefault(spiel.get("feld") or 1, []).append(spiel)
        for feld, liste in sorted(felder.items()):
            if len(liste) > 1:
                nummern = ", ".join(f"#{s['nummer']}" for s in liste)
                konflikte.append(
                    f"{uhrzeit}: {len(liste)} Spiele gleichzeitig auf Feld "
                    f"{feld} ({nummern})."
                )

        # Dieselbe Mannschaft zweimal zur selben Zeit
        teams = {}
        for spiel in gleichzeitig:
            for team in (spiel.get("teams") or ()):
                if team is not None:
                    teams.setdefault(team, []).append(spiel)
        for team, liste in teams.items():
            if len(liste) > 1:
                nummern = ", ".join(f"#{s['nummer']}" for s in liste)
                konflikte.append(
                    f"{uhrzeit}: Mannschaft {team} ist für {len(liste)} "
                    f"Spiele gleichzeitig angesetzt ({nummern})."
                )

    return konflikte
