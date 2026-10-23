"""Siegerehrung: Endplatzierung, Ablaufliste und druckbare Urkunden."""
import csv
import io
from datetime import date

from flask import (
    Blueprint, abort, current_app, flash, g, jsonify, redirect,
    render_template, request, url_for,
)
from flask_login import login_required

from app import db
from app.auth import editor_required, tournament_required
from app.models import (
    Match, Team, Tournament, calculate_overall_rankings, get_all_settings,
    set_setting,
)
from app.platzierung import endplatzierung, medaille, siegerehrung_ablauf

siegerehrung_bp = Blueprint("siegerehrung", __name__)
siegerehrung_admin_bp = Blueprint("siegerehrung_admin", __name__)


def platzierung_fuer(tournament_id):
    """Endplatzierung eines Turniers aus der Datenbank."""
    final_matches = [
        {
            "team1_id": m.team1_id,
            "team2_id": m.team2_id,
            "score_team1": m.score_team1,
            "score_team2": m.score_team2,
            "status": m.status,
            "final_round": m.final_round,
            "final_label": m.final_label,
            "is_loser_match": bool(m.is_loser_match),
        }
        for m in Match.query.filter_by(tournament_id=tournament_id,
                                       is_final=True).all()
    ]
    team_namen = {t.id: t.name for t in
                  Team.query.filter_by(tournament_id=tournament_id).all()}
    return endplatzierung(
        final_matches, calculate_overall_rankings(tournament_id), team_namen)


# ──────────────────────────────────────
# Oeffentliche Ansicht
# ──────────────────────────────────────

@siegerehrung_bp.route("/t/<slug>/platzierung")
def platzierung_seite(slug):
    tournament = Tournament.query.filter_by(slug=slug).first()
    if not tournament:
        abort(404)
    g.tournament = tournament
    einstellungen = get_all_settings(tournament.id)
    verborgen = einstellungen.get("hide_results") == "1"
    return render_template(
        "platzierung.html", tournament=tournament, verborgen=verborgen,
        platzierung=[] if verborgen else platzierung_fuer(tournament.id),
        phase=einstellungen.get("tournament_phase", "GROUP_STAGE"),
        medaille=medaille,
    )


@siegerehrung_bp.route("/t/<slug>/api/platzierung")
def platzierung_api(slug):
    tournament = Tournament.query.filter_by(slug=slug).first()
    if not tournament:
        return jsonify({"error": "not found"}), 404
    if get_all_settings(tournament.id).get("hide_results") == "1":
        return jsonify({"verborgen": True})
    return jsonify({"platzierung": platzierung_fuer(tournament.id)})


# ──────────────────────────────────────
# Adminbereich
# ──────────────────────────────────────

@siegerehrung_admin_bp.route("/t/<slug>/siegerehrung")
@login_required
@tournament_required
def uebersicht():
    t = g.tournament
    platzierung = platzierung_fuer(t.id)
    return render_template(
        "admin/siegerehrung.html", tournament=t,
        platzierung=platzierung,
        ablauf=siegerehrung_ablauf(platzierung),
        einstellungen=get_all_settings(t.id),
        medaille=medaille,
    )


@siegerehrung_admin_bp.route("/t/<slug>/siegerehrung/einstellungen",
                             methods=["POST"])
@login_required
@editor_required
@tournament_required
def einstellungen_speichern():
    t = g.tournament
    felder = {
        "urkunde_veranstalter": 150,
        "urkunde_ort": 100,
        "urkunde_text": 500,
        "urkunde_unterschrift": 100,
    }
    for schluessel, maxlen in felder.items():
        set_setting(t.id, schluessel,
                    (request.form.get(schluessel) or "").strip()[:maxlen])
    set_setting(t.id, "urkunde_alle_teams",
                "1" if request.form.get("urkunde_alle_teams") == "1" else "0")
    flash("Urkunden-Einstellungen gespeichert.", "success")
    return redirect(url_for("siegerehrung_admin.uebersicht", slug=t.slug))


@siegerehrung_admin_bp.route("/t/<slug>/urkunden")
@login_required
@tournament_required
def urkunden():
    """Druckansicht: eine Urkunde pro Seite.

    ?nur=1,2,3 beschraenkt auf bestimmte Plaetze – praktisch, wenn man nur
    das Podium drucken will oder eine Urkunde nachdrucken muss.
    """
    t = g.tournament
    einstellungen = get_all_settings(t.id)
    platzierung = platzierung_fuer(t.id)

    nur_param = (request.args.get("nur") or "").strip()
    if nur_param:
        try:
            erlaubt = {int(x) for x in nur_param.split(",") if x.strip()}
        except ValueError:
            erlaubt = None
        if erlaubt:
            platzierung = [e for e in platzierung if e["platz"] in erlaubt]
    elif einstellungen.get("urkunde_alle_teams") != "1":
        platzierung = [e for e in platzierung if e["platz"] <= 3]

    return render_template(
        "admin/urkunden.html", tournament=t, platzierung=platzierung,
        einstellungen=einstellungen, medaille=medaille,
        heute=date.today(),
    )


@siegerehrung_admin_bp.route("/t/<slug>/siegerehrung/platzierung.csv")
@login_required
@tournament_required
def platzierung_csv():
    t = g.tournament
    puffer = io.StringIO()
    writer = csv.writer(puffer, delimiter=";")
    writer.writerow(["Platz", "Mannschaft", "geteilt", "entschieden durch"])
    for e in platzierung_fuer(t.id):
        writer.writerow([e["platz"], e["team_name"] or "",
                         "ja" if e["geteilt"] else "nein", e["quelle"]])

    antwort = current_app.response_class("﻿" + puffer.getvalue(),
                                         mimetype="text/csv")
    antwort.headers["Content-Disposition"] = (
        f'attachment; filename="platzierung-{t.slug}.csv"')
    return antwort
