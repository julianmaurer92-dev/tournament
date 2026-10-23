#!/usr/bin/env python
"""Testdaten fuer die Dev-Instanz anlegen.

Erzeugt ein realistisches Turnierwochenende: drei Altersklassen, Gruppen,
Teams, Spielplan mit Anstosszeiten, teils gespielte Spiele, ein laufendes
Spiel, Speisekarte und Benutzer aller Rollen.

Ausfuehren:
    docker compose -p cupplan-dev -f docker-compose.dev.yml \
        exec web python scripts/seed_dev.py [--reset]

--reset loescht vorher alle Turniere, Speisekarte und Nicht-Admin-Benutzer.
NIEMALS gegen die Produktionsdatenbank laufen lassen.
"""
import argparse
import os
import random
import sys
from datetime import date, datetime, time, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db  # noqa: E402
from app.models import (  # noqa: E402
    Admin, Group, Match, MenuItem, Team, Tournament, TeamPayment,
    ensure_default_settings, set_setting, slugify,
)

random.seed(20261024)   # reproduzierbare Testdaten

VEREINE = [
    "SV Winkel", "TSV Oberbach", "FC Rosenheim", "SG Talheim",
    "SpVgg Au", "VfL Birkenfeld", "TuS Lindau", "FC Seefeld",
    "SV Hohenberg", "TSV Mettenberg", "FV Kirchdorf", "SC Weiler",
]

SPEISEN = [
    ("Bratwurst im Weckle", "3,00", "vom Grill"),
    ("Currywurst mit Pommes", "5,50", ""),
    ("Pommes frites", "2,50", "mit Ketchup oder Mayo"),
    ("Steak im Weckle", "4,50", ""),
    ("Pommes mit Wiener", "4,00", "fuer die Kleinen"),
    ("Kuchen (Stueck)", "2,00", "von unseren Eltern gebacken"),
    ("Waffel", "2,50", "mit Puderzucker"),
]

GETRAENKE = [
    ("Cola 0,33 l", "2,00", ""),
    ("Apfelschorle 0,33 l", "2,00", ""),
    ("Mineralwasser 0,33 l", "1,50", ""),
    ("Kaffee", "1,50", "Tasse"),
    ("Weizenbier 0,5 l", "3,50", "ab 16 Jahren"),
    ("Radler 0,5 l", "3,50", ""),
]


def _round_robin(teams):
    """Jeder gegen jeden, als Liste von (team_a, team_b)."""
    paare = []
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            paare.append((teams[i], teams[j]))
    return paare


def build_tournament(name, tag, startzeit, gruppen_namen, teams_pro_gruppe,
                     spielzeit_min, order, beschreibung,
                     gespielt_anteil=0.0, live_spiel=False):
    """Ein Turnier mit Gruppen, Teams und Spielplan anlegen."""
    t = Tournament(
        name=name,
        slug=slugify(name),
        description=beschreibung,
        event_date=tag,
        event_time=startzeit.strftime("%H:%M"),
        is_active=True,
        display_order=order,
    )
    db.session.add(t)
    db.session.commit()
    ensure_default_settings(t.id)
    set_setting(t.id, "tournament_name", name.upper())
    set_setting(t.id, "default_timer_regular", str(spielzeit_min * 60))
    set_setting(t.id, "num_fields", "2")
    set_setting(t.id, "tournament_rules", (
        f"Spielzeit {spielzeit_min} Minuten ohne Seitenwechsel.\n"
        "Es gilt die Jugendordnung des Verbands.\n"
        "Bei Punktgleichheit entscheidet die Tordifferenz, dann die "
        "Anzahl der erzielten Tore, dann das Neunmeterschiessen."
    ))

    verein_pool = VEREINE.copy()
    random.shuffle(verein_pool)

    gruppen = []
    alle_teams = []
    for gi, gname in enumerate(gruppen_namen):
        gr = Group(tournament_id=t.id, name=gname, display_order=gi)
        db.session.add(gr)
        db.session.commit()
        gruppen.append(gr)
        for _ in range(teams_pro_gruppe):
            vname = verein_pool.pop()
            tm = Team(tournament_id=t.id, name=vname, group_id=gr.id,
                      players="")
            db.session.add(tm)
            db.session.commit()
            db.session.add(TeamPayment(
                team_id=tm.id, paid=random.random() < 0.7,
                amount=25.0,
            ))
            alle_teams.append(tm)
    db.session.commit()

    # Spielplan: Gruppenspiele abwechselnd auf Feld 1 und 2
    begegnungen = []
    for gr in gruppen:
        gruppen_teams = [tm for tm in alle_teams if tm.group_id == gr.id]
        for a, b in _round_robin(gruppen_teams):
            begegnungen.append((gr, a, b))
    random.shuffle(begegnungen)

    anstoss = datetime.combine(tag, startzeit)
    slot_laenge = timedelta(minutes=spielzeit_min + 5)
    matches = []
    for idx, (gr, a, b) in enumerate(begegnungen):
        feld = (idx % 2) + 1
        # Zwei Felder spielen parallel -> nach je zwei Spielen neuer Slot
        slot = idx // 2
        m = Match(
            tournament_id=t.id, team1_id=a.id, team2_id=b.id,
            group_id=gr.id, match_order=idx + 1, field=feld,
            scheduled_time=anstoss + slot * slot_laenge,
            timer_duration=spielzeit_min * 60,
            timer_remaining=spielzeit_min * 60,
        )
        db.session.add(m)
        matches.append(m)
    db.session.commit()

    # Einen Teil der Spiele als gespielt markieren
    anzahl_fertig = int(len(matches) * gespielt_anteil)
    for m in matches[:anzahl_fertig]:
        m.score_team1 = random.choice([0, 0, 1, 1, 2, 2, 3, 4])
        m.score_team2 = random.choice([0, 0, 1, 1, 2, 2, 3, 4])
        m.status = "finished"
    if live_spiel and len(matches) > anzahl_fertig:
        lm = matches[anzahl_fertig]
        lm.status = "live"
        lm.score_team1 = 1
        lm.score_team2 = 0
        lm.timer_remaining = spielzeit_min * 60 - 240
    db.session.commit()

    print(f"  {name}: {len(gruppen)} Gruppen, {len(alle_teams)} Teams, "
          f"{len(matches)} Spiele ({anzahl_fertig} gespielt)")
    return t


def seed_menu():
    bestehend = {mi.name for mi in MenuItem.query.all()}
    order = 0
    for name, preis, beschreibung in SPEISEN:
        order += 1
        if name in bestehend:
            continue
        db.session.add(MenuItem(name=name, price=preis, category="speise",
                                description=beschreibung, display_order=order))
    order = 0
    for name, preis, beschreibung in GETRAENKE:
        order += 1
        if name in bestehend:
            continue
        db.session.add(MenuItem(name=name, price=preis, category="getraenk",
                                description=beschreibung, display_order=order))
    db.session.commit()
    print(f"  Speisekarte: {MenuItem.query.count()} Eintraege")


def seed_users():
    """Je ein Benutzer pro Rolle (Passwort jeweils 'dev12345')."""
    gewuenscht = [
        ("spielleiter", "editor"),
        ("anzeigetafel", "viewer"),
    ]
    for username, rolle in gewuenscht:
        if Admin.query.filter_by(username=username).first():
            continue
        u = Admin(username=username, role=rolle)
        u.set_password("dev12345")
        db.session.add(u)
    db.session.commit()
    print("  Benutzer: admin (superadmin), spielleiter (editor), "
          "anzeigetafel (viewer) – Passwort der Testbenutzer: dev12345")


def reset():
    print("  Loesche bestehende Testdaten ...")
    for t in Tournament.query.all():
        db.session.delete(t)
    MenuItem.query.delete()
    Admin.query.filter(Admin.username != "admin").delete()
    db.session.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true",
                        help="bestehende Daten vorher loeschen")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        uri = app.config["SQLALCHEMY_DATABASE_URI"]
        if "cupplan_dev" not in uri and "sqlite" not in uri:
            sys.exit(f"ABBRUCH: Datenbank sieht nicht nach Dev aus: {uri}")

        print("Seed-Daten fuer CupPlan-Dev")
        if args.reset:
            reset()

        samstag = date(2026, 11, 14)
        sonntag = date(2026, 11, 15)

        build_tournament(
            "E-Jugend Winkelturnier 2026", samstag, time(9, 0),
            ["Gruppe A", "Gruppe B"], 4, 10, order=1,
            beschreibung="E-Jugend (Jahrgang 2017/2018), 8 Mannschaften",
            gespielt_anteil=1.0,
        )
        build_tournament(
            "D-Jugend Winkelturnier 2026", samstag, time(13, 30),
            ["Gruppe A", "Gruppe B"], 3, 12, order=2,
            beschreibung="D-Jugend (Jahrgang 2015/2016), 6 Mannschaften",
            gespielt_anteil=0.5, live_spiel=True,
        )
        build_tournament(
            "F-Jugend Winkelturnier 2026", sonntag, time(10, 0),
            ["Gruppe A"], 5, 8, order=3,
            beschreibung="F-Jugend (Jahrgang 2019/2020), Spielrunde ohne Tabelle",
            gespielt_anteil=0.0,
        )

        seed_menu()
        seed_users()
        print("Fertig. Dev-Instanz: http://localhost:8090")


if __name__ == "__main__":
    main()
