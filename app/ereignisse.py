"""Spielereignisse erfassen und auswerten.

Tore und Karten werden je Spiel eingetragen. Daraus entstehen die
Torschuetzenliste und die Fair-Play-Wertung des Turniers.

Verhaeltnis zum Spielstand
--------------------------
Der Spielstand am Match bleibt die fuehrende Zahl – er wird am Turniertag
ueber die Plus-Knoepfe in der Spielsteuerung gesetzt und darf nie von einer
unvollstaendigen Ereignisliste ueberschrieben werden. Wer ein Tor mit
Schuetzen erfasst, bekommt den Spielstand aber per Vorgabe mitgezogen
(`ergebnis_anpassen`), damit man nicht alles doppelt tippen muss. Weichen
beide voneinander ab, zeigt die Oberflaeche das als Hinweis an, statt
stillschweigend eine der beiden Zahlen zu bevorzugen.
"""
import csv
import io

from flask import (
    Blueprint, abort, current_app, flash, g, jsonify, redirect,
    render_template, request, url_for,
)
from flask_login import login_required

from app import db
from app.auth import editor_required, tournament_required
from app.models import (
    EREIGNIS_ARTEN, EREIGNIS_EIGENTOR, EREIGNIS_LABEL, EREIGNIS_TOR,
    Match, MatchEvent, Team, Tournament, get_all_settings,
)
from app.socket_events import broadcast_state
from app.statistik import (
    ergebnis_stimmt, fairplay_tabelle, karten_je_spieler, tore_ohne_schuetzen,
    torschuetzenliste,
)

ereignisse_bp = Blueprint("ereignisse", __name__)
ereignisse_admin_bp = Blueprint("ereignisse_admin", __name__)


def _ereignisse_als_dicts(query):
    return [
        {
            "art": e.art,
            "team_id": e.team_id,
            "team_name": e.team.name if e.team else None,
            "player_name": e.player_name,
            "minute": e.minute,
        }
        for e in query
    ]


def turnier_statistik(tournament_id):
    """Torschuetzen, Fair-Play und Karten je Spieler fuer ein Turnier."""
    ereignisse = _ereignisse_als_dicts(
        MatchEvent.query.filter_by(tournament_id=tournament_id).all())
    teams = [(t.id, t.name) for t in
             Team.query.filter_by(tournament_id=tournament_id)
             .order_by(Team.name).all()]
    return {
        "torschuetzen": torschuetzenliste(ereignisse),
        "tore_ohne_schuetzen": tore_ohne_schuetzen(ereignisse),
        "fairplay": fairplay_tabelle(ereignisse, teams),
        "karten_spieler": karten_je_spieler(ereignisse),
        "anzahl_ereignisse": len(ereignisse),
    }


# ──────────────────────────────────────
# Oeffentliche Ansicht
# ──────────────────────────────────────

@ereignisse_bp.route("/t/<slug>/statistik")
def statistik_seite(slug):
    tournament = Tournament.query.filter_by(slug=slug).first()
    if not tournament:
        abort(404)
    g.tournament = tournament
    einstellungen = get_all_settings(tournament.id)
    # Wer Ergebnisse ausblendet, will auch keine Torschuetzenliste zeigen
    verborgen = einstellungen.get("hide_results") == "1"
    return render_template(
        "statistik.html", tournament=tournament, verborgen=verborgen,
        **({} if verborgen else turnier_statistik(tournament.id)),
    )


@ereignisse_bp.route("/t/<slug>/api/statistik")
def statistik_api(slug):
    tournament = Tournament.query.filter_by(slug=slug).first()
    if not tournament:
        return jsonify({"error": "not found"}), 404
    if get_all_settings(tournament.id).get("hide_results") == "1":
        return jsonify({"verborgen": True})
    return jsonify(turnier_statistik(tournament.id))


# ──────────────────────────────────────
# Erfassung im Adminbereich
# ──────────────────────────────────────

def _spiel_oder_404(mid):
    t = g.tournament
    match = db.session.get(Match, mid)
    if not match or match.tournament_id != t.id:
        abort(404)
    return match


@ereignisse_admin_bp.route("/t/<slug>/matches/<int:mid>/ereignisse")
@login_required
@tournament_required
def spiel_ereignisse(mid):
    """Erfassungsmaske fuer ein einzelnes Spiel."""
    t = g.tournament
    match = _spiel_oder_404(mid)
    ereignisse = match.events.all()
    stimmt, tore1, tore2 = ergebnis_stimmt(
        match.score_team1, match.score_team2,
        match.team1_id, match.team2_id,
        _ereignisse_als_dicts(ereignisse),
    )
    return render_template(
        "admin/ereignisse.html", tournament=t, match=match,
        ereignisse=ereignisse, arten=EREIGNIS_LABEL,
        ergebnis_stimmt=stimmt, tore_team1=tore1, tore_team2=tore2,
        spieler_vorschlaege=_spieler_vorschlaege(match),
    )


def _spieler_vorschlaege(match):
    """Spielernamen aus dem Teamfeld 'players' als Vorschlagsliste.

    Team.players ist ein Textfeld – eine Zeile oder ein Komma je Spieler.
    Beides wird akzeptiert, Trikotnummern am Anfang bleiben stehen.
    """
    vorschlaege = {}
    for team in (match.team1, match.team2):
        if not team:
            continue
        namen = []
        for zeile in (team.players or "").replace(",", "\n").split("\n"):
            name = zeile.strip()
            if name:
                namen.append(name)
        vorschlaege[team.id] = namen
    return vorschlaege


@ereignisse_admin_bp.route("/t/<slug>/api/matches/<int:mid>/ereignisse",
                           methods=["GET"])
@login_required
@tournament_required
def ereignisse_lesen(mid):
    match = _spiel_oder_404(mid)
    ereignisse = match.events.all()
    stimmt, tore1, tore2 = ergebnis_stimmt(
        match.score_team1, match.score_team2,
        match.team1_id, match.team2_id,
        _ereignisse_als_dicts(ereignisse),
    )
    return jsonify({
        "ereignisse": [e.to_dict() for e in ereignisse],
        "ergebnis_stimmt": stimmt,
        "tore_aus_ereignissen": {"team1": tore1, "team2": tore2},
        "ergebnis": {"team1": match.score_team1, "team2": match.score_team2},
    })


@ereignisse_admin_bp.route("/t/<slug>/api/matches/<int:mid>/ereignisse",
                           methods=["POST"])
@login_required
@editor_required
@tournament_required
def ereignis_anlegen(mid):
    """Ereignis erfassen.

    Pflicht: art, team_id. Optional: player_name, minute, note,
    ergebnis_anpassen (Vorgabe: ja – bei Toren wird der Spielstand mitgezogen).
    """
    t = g.tournament
    match = _spiel_oder_404(mid)
    daten = request.get_json(silent=True) or request.form

    art = (daten.get("art") or "").strip()
    if art not in EREIGNIS_ARTEN:
        return jsonify({"error": "Unbekannte Ereignisart."}), 400

    team_id = daten.get("team_id")
    try:
        team_id = int(team_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Mannschaft fehlt."}), 400
    if team_id not in (match.team1_id, match.team2_id):
        return jsonify({"error": "Diese Mannschaft spielt nicht in "
                                 "diesem Spiel."}), 400

    minute = daten.get("minute")
    if minute in (None, ""):
        minute = None
    else:
        try:
            minute = int(minute)
        except (TypeError, ValueError):
            return jsonify({"error": "Minute muss eine Zahl sein."}), 400
        if minute < 0 or minute > 200:
            return jsonify({"error": "Minute ausserhalb des Spielzeitraums."}), 400

    ereignis = MatchEvent(
        match_id=match.id,
        tournament_id=t.id,
        art=art,
        # Ein Eigentor wird dem begünstigten Team zugeschrieben, damit die
        # Torsumme zum Ergebnis passt. Der Schuetze steht in der Notiz.
        team_id=_gegner(match, team_id) if art == EREIGNIS_EIGENTOR else team_id,
        player_name=(daten.get("player_name") or "").strip()[:150],
        minute=minute,
        note=(daten.get("note") or "").strip()[:300],
    )
    if art == EREIGNIS_EIGENTOR and ereignis.player_name:
        ereignis.note = (f"Eigentor von {ereignis.player_name}"
                         + (f" – {ereignis.note}" if ereignis.note else ""))
        ereignis.player_name = ""

    db.session.add(ereignis)

    if art in (EREIGNIS_TOR, EREIGNIS_EIGENTOR) and _soll_anpassen(daten):
        _ergebnis_verschieben(match, ereignis.team_id, +1)

    db.session.commit()
    broadcast_state(t.id)
    return jsonify({"ok": True, "ereignis": ereignis.to_dict(),
                    "ergebnis": {"team1": match.score_team1,
                                 "team2": match.score_team2}})


def _soll_anpassen(daten):
    """Soll der Spielstand mitgezogen werden? Vorgabe: ja."""
    wert = daten.get("ergebnis_anpassen")
    if wert is None:
        return True
    return str(wert).strip().lower() in ("1", "true", "on", "ja", "yes")


def _gegner(match, team_id):
    return match.team2_id if team_id == match.team1_id else match.team1_id


def _ergebnis_verschieben(match, team_id, delta):
    """Spielstand einer Seite um delta aendern, nie unter null."""
    if team_id == match.team1_id:
        match.score_team1 = max(0, (match.score_team1 or 0) + delta)
    elif team_id == match.team2_id:
        match.score_team2 = max(0, (match.score_team2 or 0) + delta)


@ereignisse_admin_bp.route(
    "/t/<slug>/api/ereignisse/<int:eid>/loeschen", methods=["POST"])
@login_required
@editor_required
@tournament_required
def ereignis_loeschen(eid):
    t = g.tournament
    ereignis = db.session.get(MatchEvent, eid)
    if not ereignis or ereignis.tournament_id != t.id:
        abort(404)

    match = db.session.get(Match, ereignis.match_id)
    daten = request.get_json(silent=True) or request.form or {}
    if (match and ereignis.art in (EREIGNIS_TOR, EREIGNIS_EIGENTOR)
            and _soll_anpassen(daten)):
        _ergebnis_verschieben(match, ereignis.team_id, -1)

    db.session.delete(ereignis)
    db.session.commit()
    broadcast_state(t.id)
    return jsonify({"ok": True,
                    "ergebnis": {"team1": match.score_team1,
                                 "team2": match.score_team2} if match else None})


# ──────────────────────────────────────
# Auswertung im Adminbereich
# ──────────────────────────────────────

@ereignisse_admin_bp.route("/t/<slug>/statistik")
@login_required
@tournament_required
def statistik_admin():
    t = g.tournament
    return render_template("admin/statistik.html", tournament=t,
                           **turnier_statistik(t.id))


@ereignisse_admin_bp.route("/t/<slug>/statistik/torschuetzen.csv")
@login_required
@tournament_required
def torschuetzen_csv():
    t = g.tournament
    daten = turnier_statistik(t.id)

    puffer = io.StringIO()
    writer = csv.writer(puffer, delimiter=";")
    writer.writerow(["Platz", "Spieler", "Mannschaft", "Tore"])
    for eintrag in daten["torschuetzen"]:
        writer.writerow([eintrag["platz"], eintrag["player_name"],
                         eintrag["team_name"] or "", eintrag["tore"]])

    antwort = current_app.response_class("﻿" + puffer.getvalue(),
                                         mimetype="text/csv")
    antwort.headers["Content-Disposition"] = (
        f'attachment; filename="torschuetzen-{t.slug}.csv"')
    return antwort
