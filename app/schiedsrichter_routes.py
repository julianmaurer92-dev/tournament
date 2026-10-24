"""Schiedsrichter verwalten, zuteilen und den Einsatzplan drucken."""
import csv
import io

from flask import (
    Blueprint, abort, current_app, flash, g, jsonify, redirect,
    render_template, request, url_for,
)
from flask_login import login_required

from app import db
from app.auth import editor_required, superadmin_required, tournament_required
from app.models import Match, Referee, Team, get_all_settings
from app.schiedsrichter import (
    einsatzzahlen, finde_schiedsrichter_konflikte, verteile_schiedsrichter,
)
from app.socket_events import broadcast_state

schiedsrichter_bp = Blueprint("schiedsrichter", __name__)


def _spiele_als_dicts(tournament_id):
    spiele = Match.query.filter_by(tournament_id=tournament_id).order_by(
        Match.scheduled_time, Match.match_order).all()
    return spiele, [
        {
            "id": m.id,
            "nummer": m.match_order,
            "anstoss": m.scheduled_time,
            "feld": m.field or 1,
            "teams": (m.team1_id, m.team2_id),
            "schiedsrichter_id": m.referee_id,
        }
        for m in spiele
    ]


def _schiedsrichter_als_dicts(tournament_id):
    schiris = Referee.query.filter_by(tournament_id=tournament_id).order_by(
        Referee.name).all()
    return schiris, [
        {"id": s.id, "name": s.name, "team_id": s.team_id,
         "aktiv": bool(s.is_active)}
        for s in schiris
    ]


@schiedsrichter_bp.route("/t/<slug>/schiedsrichter")
@login_required
@tournament_required
def uebersicht():
    t = g.tournament
    schiris, schiri_dicts = _schiedsrichter_als_dicts(t.id)
    spiele, spiel_dicts = _spiele_als_dicts(t.id)
    teams = Team.query.filter_by(tournament_id=t.id).order_by(Team.name).all()

    return render_template(
        "admin/schiedsrichter.html", tournament=t,
        schiedsrichter=schiris, teams=teams, spiele=spiele,
        einsaetze=einsatzzahlen(spiel_dicts, schiri_dicts),
        konflikte=finde_schiedsrichter_konflikte(spiel_dicts, schiri_dicts),
        ohne_schiedsrichter=sum(1 for s in spiel_dicts
                                if not s["schiedsrichter_id"]),
    )


# ──────────────────────────────────────
# Stammdaten
# ──────────────────────────────────────

@schiedsrichter_bp.route("/t/<slug>/schiedsrichter/neu", methods=["POST"])
@login_required
@editor_required
@tournament_required
def anlegen():
    t = g.tournament
    name = (request.form.get("name") or "").strip()[:150]
    if not name:
        flash("Name erforderlich.", "error")
        return redirect(url_for("schiedsrichter.uebersicht", slug=t.slug))
    if Referee.query.filter_by(tournament_id=t.id, name=name).first():
        flash(f"'{name}' ist schon eingetragen.", "error")
        return redirect(url_for("schiedsrichter.uebersicht", slug=t.slug))

    team_id = request.form.get("team_id", type=int)
    if team_id:
        team = db.session.get(Team, team_id)
        if not team or team.tournament_id != t.id:
            team_id = None

    db.session.add(Referee(
        tournament_id=t.id, name=name,
        phone=(request.form.get("phone") or "").strip()[:60],
        note=(request.form.get("note") or "").strip()[:300],
        team_id=team_id or None,
    ))
    db.session.commit()
    flash(f"Schiedsrichter '{name}' angelegt.", "success")
    return redirect(url_for("schiedsrichter.uebersicht", slug=t.slug))


def _schiri_oder_404(sid):
    t = g.tournament
    schiri = db.session.get(Referee, sid)
    if not schiri or schiri.tournament_id != t.id:
        abort(404)
    return schiri


@schiedsrichter_bp.route("/t/<slug>/schiedsrichter/<int:sid>/bearbeiten",
                         methods=["POST"])
@login_required
@editor_required
@tournament_required
def bearbeiten(sid):
    t = g.tournament
    schiri = _schiri_oder_404(sid)

    name = (request.form.get("name") or "").strip()[:150]
    if name and name != schiri.name:
        if Referee.query.filter_by(tournament_id=t.id, name=name).first():
            flash(f"'{name}' ist schon eingetragen.", "error")
            return redirect(url_for("schiedsrichter.uebersicht", slug=t.slug))
        schiri.name = name

    schiri.phone = (request.form.get("phone") or "").strip()[:60]
    schiri.note = (request.form.get("note") or "").strip()[:300]
    team_id = request.form.get("team_id", type=int)
    if team_id:
        team = db.session.get(Team, team_id)
        schiri.team_id = team.id if team and team.tournament_id == t.id else None
    else:
        schiri.team_id = None
    schiri.is_active = request.form.get("is_active") == "1"

    db.session.commit()
    flash(f"'{schiri.name}' aktualisiert.", "success")
    return redirect(url_for("schiedsrichter.uebersicht", slug=t.slug))


@schiedsrichter_bp.route("/t/<slug>/schiedsrichter/<int:sid>/loeschen",
                         methods=["POST"])
@login_required
@superadmin_required
@tournament_required
def loeschen(sid):
    t = g.tournament
    schiri = _schiri_oder_404(sid)
    name = schiri.name
    anzahl = schiri.matches.count()
    db.session.delete(schiri)
    db.session.commit()
    broadcast_state(t.id)
    if anzahl:
        flash(f"'{name}' gelöscht. {anzahl} Spiel(e) sind jetzt ohne "
              "Schiedsrichter.", "success")
    else:
        flash(f"'{name}' gelöscht.", "success")
    return redirect(url_for("schiedsrichter.uebersicht", slug=t.slug))


# ──────────────────────────────────────
# Zuteilung
# ──────────────────────────────────────

@schiedsrichter_bp.route(
    "/t/<slug>/api/matches/<int:mid>/schiedsrichter", methods=["POST"])
@login_required
@editor_required
@tournament_required
def zuteilen(mid):
    """Einem Spiel einen Schiedsrichter zuordnen oder die Zuordnung loesen."""
    t = g.tournament
    match = db.session.get(Match, mid)
    if not match or match.tournament_id != t.id:
        return jsonify({"error": "Spiel nicht gefunden."}), 404

    daten = request.get_json(silent=True) or request.form
    rohwert = daten.get("schiedsrichter_id")
    if rohwert in (None, "", "0"):
        match.referee_id = None
    else:
        try:
            sid = int(rohwert)
        except (TypeError, ValueError):
            return jsonify({"error": "Ungültige Schiedsrichter-ID."}), 400
        schiri = db.session.get(Referee, sid)
        if not schiri or schiri.tournament_id != t.id:
            return jsonify({"error": "Schiedsrichter nicht gefunden."}), 404
        match.referee_id = schiri.id

    db.session.commit()
    broadcast_state(t.id)
    return jsonify({"ok": True, "match": match.to_dict()})


@schiedsrichter_bp.route("/t/<slug>/api/schiedsrichter/verteilen",
                         methods=["POST"])
@login_required
@editor_required
@tournament_required
def verteilen():
    """Automatisch zuteilen.

    nur_leere=True (Vorgabe) fuellt nur Spiele ohne Schiedsrichter auf und
    laesst eine von Hand gemachte Einteilung in Ruhe.
    """
    t = g.tournament
    daten = request.get_json(silent=True) or request.form or {}
    nur_leere = str(daten.get("nur_leere", "1")).lower() not in (
        "0", "false", "nein", "off")

    spiele, spiel_dicts = _spiele_als_dicts(t.id)
    _schiris, schiri_dicts = _schiedsrichter_als_dicts(t.id)
    if not schiri_dicts:
        return jsonify({"error": "Es sind keine Schiedsrichter angelegt."}), 400

    zuteilung, offen = verteile_schiedsrichter(
        spiel_dicts, schiri_dicts, nur_leere=nur_leere)

    nach_id = {m.id: m for m in spiele}
    if not nur_leere:
        for m in spiele:
            m.referee_id = None
    for spiel_id, schiri_id in zuteilung.items():
        nach_id[spiel_id].referee_id = schiri_id
    db.session.commit()
    broadcast_state(t.id)

    _spiele2, spiel_dicts2 = _spiele_als_dicts(t.id)
    return jsonify({
        "ok": True,
        "zugeteilt": len(zuteilung),
        "offen": len(offen),
        "konflikte": finde_schiedsrichter_konflikte(spiel_dicts2, schiri_dicts),
    })


@schiedsrichter_bp.route("/t/<slug>/api/schiedsrichter/konflikte")
@login_required
@tournament_required
def konflikte():
    t = g.tournament
    _spiele, spiel_dicts = _spiele_als_dicts(t.id)
    _schiris, schiri_dicts = _schiedsrichter_als_dicts(t.id)
    liste = finde_schiedsrichter_konflikte(spiel_dicts, schiri_dicts)
    return jsonify({"konflikte": liste, "anzahl": len(liste)})


# ──────────────────────────────────────
# Einsatzplan
# ──────────────────────────────────────

@schiedsrichter_bp.route("/t/<slug>/schiedsrichter/plan")
@login_required
@tournament_required
def einsatzplan():
    """Druckbarer Einsatzplan – je Schiedsrichter eine Liste."""
    t = g.tournament
    schiris, schiri_dicts = _schiedsrichter_als_dicts(t.id)
    spiele, spiel_dicts = _spiele_als_dicts(t.id)

    plan = []
    for schiri in schiris:
        eigene = [m for m in spiele if m.referee_id == schiri.id]
        plan.append({"schiedsrichter": schiri, "spiele": eigene})
    ohne = [m for m in spiele if not m.referee_id]

    return render_template(
        "admin/schiedsrichter_plan.html", tournament=t, plan=plan,
        ohne=ohne, einstellungen=get_all_settings(t.id),
    )


@schiedsrichter_bp.route("/t/<slug>/schiedsrichter/plan.csv")
@login_required
@tournament_required
def einsatzplan_csv():
    t = g.tournament
    spiele, _dicts = _spiele_als_dicts(t.id)

    puffer = io.StringIO()
    writer = csv.writer(puffer, delimiter=";")
    writer.writerow(["Spiel", "Anstoss", "Feld", "Begegnung",
                     "Schiedsrichter", "Telefon"])
    for m in spiele:
        writer.writerow([
            m.match_order,
            m.scheduled_time.strftime("%d.%m.%Y %H:%M") if m.scheduled_time else "",
            m.field or 1,
            f"{m.team1.name if m.team1 else '?'} - "
            f"{m.team2.name if m.team2 else '?'}",
            m.referee.name if m.referee else "",
            m.referee.phone if m.referee else "",
        ])

    antwort = current_app.response_class("﻿" + puffer.getvalue(),
                                         mimetype="text/csv")
    antwort.headers["Content-Disposition"] = (
        f'attachment; filename="schiedsrichter-{t.slug}.csv"')
    return antwort
