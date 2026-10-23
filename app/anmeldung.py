"""Vereinsanmeldung: oeffentliches Formular und Freigabe im Adminbereich.

Ablauf
------
1. Der Veranstalter schaltet die Anmeldung je Turnier frei (Frist, maximale
   Teamzahl, Startgebuehr, Infotext).
2. Vereine melden sich unter /t/<slug>/anmeldung an und bekommen einen Link
   auf eine Statusseite, ueber die sie ihre Anmeldung auch zuruecknehmen
   koennen.
3. Der Veranstalter bestaetigt, lehnt ab oder setzt auf die Warteliste.
   Beim Bestaetigen entsteht das Team im Spielplan – optional direkt in
   einer Gruppe und mit offener Startgebuehr.
"""
import csv
import io
import re
from datetime import date, datetime, timezone

from flask import (
    Blueprint, abort, current_app, flash, g, jsonify, redirect,
    render_template, request, url_for,
)
from flask_login import current_user, login_required

from app import db
from app.auth import editor_required, superadmin_required, tournament_required
from app.models import (
    ANMELDUNG_ABGELEHNT, ANMELDUNG_BESTAETIGT, ANMELDUNG_OFFEN,
    ANMELDUNG_STATUS, ANMELDUNG_WARTELISTE, Group, Registration, Team,
    TeamPayment, Tournament, anmeldungen_zaehlen, get_all_settings,
    get_setting, set_setting,
)
from app.security import formularbremse
from app.socket_events import broadcast_state

anmeldung_bp = Blueprint("anmeldung", __name__)

# Absichtlich grosszuegig: "a@b.de" soll durchgehen, "keine mail" nicht.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]{2,}$")

MAX_LAENGEN = {
    "club_name": 150,
    "team_name": 150,
    "contact_name": 150,
    "contact_email": 254,
    "contact_phone": 60,
    "notes": 2000,
}


# ──────────────────────────────────────
# Regeln rund um die Anmeldefrist
# ──────────────────────────────────────

def _heute():
    """Eigene Funktion, damit Tests das Datum ersetzen koennen."""
    return date.today()


def anmeldestatus(tournament_id):
    """Ist die Anmeldung offen? Liefert (offen, grund, infos).

    grund ist None, wenn offen – sonst ein Text fuer die Besucherseite.
    """
    s = get_all_settings(tournament_id)
    infos = {
        "deadline": None,
        "max_teams": None,
        "fee": (s.get("registration_fee") or "").strip(),
        "info": (s.get("registration_info") or "").strip(),
        "bestaetigt": 0,
        "frei": None,
    }

    frist_text = (s.get("registration_deadline") or "").strip()
    if frist_text:
        try:
            infos["deadline"] = date.fromisoformat(frist_text)
        except ValueError:
            infos["deadline"] = None

    max_text = (s.get("registration_max_teams") or "").strip()
    if max_text:
        try:
            infos["max_teams"] = max(0, int(max_text))
        except ValueError:
            infos["max_teams"] = None

    zahlen = anmeldungen_zaehlen(tournament_id)
    # Bestaetigte Anmeldungen und bereits bestehende Teams belegen Plaetze
    team_anzahl = Team.query.filter_by(tournament_id=tournament_id).count()
    infos["bestaetigt"] = max(zahlen[ANMELDUNG_BESTAETIGT], team_anzahl)
    if infos["max_teams"] is not None:
        infos["frei"] = max(0, infos["max_teams"] - infos["bestaetigt"])

    if (s.get("registration_open") or "0") != "1":
        return False, "Die Anmeldung für dieses Turnier ist nicht geöffnet.", infos

    if infos["deadline"] and _heute() > infos["deadline"]:
        return False, (
            "Die Anmeldefrist ist am "
            f"{infos['deadline'].strftime('%d.%m.%Y')} abgelaufen."
        ), infos

    if infos["frei"] == 0:
        return False, (
            "Das Turnier ist mit "
            f"{infos['max_teams']} Mannschaften ausgebucht. "
            "Du kannst dich trotzdem melden – wir führen eine Warteliste."
        ), infos

    return True, None, infos


# ──────────────────────────────────────
# Oeffentliches Formular
# ──────────────────────────────────────

def _turnier_oder_404(slug):
    tournament = Tournament.query.filter_by(slug=slug).first()
    if not tournament:
        abort(404)
    return tournament


def _absender_ip():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    return ip.split(",")[0].strip()


def _formular_pruefen(form):
    """Eingaben pruefen und saeubern. Liefert (daten, fehler)."""
    daten = {}
    fehler = {}

    for feld in ("club_name", "team_name", "contact_name",
                 "contact_email", "contact_phone", "notes"):
        wert = (form.get(feld) or "").strip()
        if len(wert) > MAX_LAENGEN[feld]:
            wert = wert[:MAX_LAENGEN[feld]]
        daten[feld] = wert

    if not daten["club_name"]:
        fehler["club_name"] = "Bitte den Vereinsnamen angeben."
    if not daten["contact_name"]:
        fehler["contact_name"] = "Bitte einen Ansprechpartner angeben."
    if not daten["contact_email"]:
        fehler["contact_email"] = "Bitte eine E-Mail-Adresse angeben."
    elif not _EMAIL_RE.match(daten["contact_email"]):
        fehler["contact_email"] = "Diese E-Mail-Adresse sieht nicht richtig aus."

    anzahl_text = (form.get("player_count") or "").strip()
    daten["player_count"] = None
    if anzahl_text:
        try:
            anzahl = int(anzahl_text)
            if anzahl < 1 or anzahl > 99:
                fehler["player_count"] = "Bitte eine Zahl zwischen 1 und 99."
            else:
                daten["player_count"] = anzahl
        except ValueError:
            fehler["player_count"] = "Bitte eine Zahl angeben."

    return daten, fehler


@anmeldung_bp.route("/t/<slug>/anmeldung", methods=["GET", "POST"])
def anmeldeformular(slug):
    tournament = _turnier_oder_404(slug)
    g.tournament = tournament
    offen, grund, infos = anmeldestatus(tournament.id)

    if request.method == "GET":
        return render_template(
            "anmeldung_form.html", tournament=tournament,
            offen=offen, grund=grund, infos=infos,
            daten={}, fehler={},
        )

    # ── POST ───────────────────────────
    # Honeypot: ein fuer Menschen unsichtbares Feld. Ist es gefuellt, war es
    # ein Bot. Wir antworten mit der normalen Dankesseite, damit der Bot
    # nichts lernt, speichern aber nichts.
    if (request.form.get("website") or "").strip():
        current_app.logger.info("Anmeldung verworfen (Honeypot), IP %s",
                                _absender_ip())
        return render_template("anmeldung_danke.html", tournament=tournament,
                               anmeldung=None, honeypot=True)

    schluessel = f"anmeldung|{_absender_ip()}"
    rest = formularbremse.restsperre(schluessel)
    if rest:
        flash("Zu viele Anmeldungen in kurzer Zeit. Bitte später erneut "
              "versuchen oder den Veranstalter direkt anschreiben.", "error")
        return render_template(
            "anmeldung_form.html", tournament=tournament,
            offen=offen, grund=grund, infos=infos,
            daten=request.form.to_dict(), fehler={},
        ), 429

    daten, fehler = _formular_pruefen(request.form)

    # Doppelte Anmeldung desselben Vereins verhindern (ausser abgelehnte)
    if not fehler:
        doppelt = Registration.query.filter(
            Registration.tournament_id == tournament.id,
            db.func.lower(Registration.club_name) == daten["club_name"].lower(),
            Registration.status != ANMELDUNG_ABGELEHNT,
        ).first()
        if doppelt:
            fehler["club_name"] = (
                "Für diesen Verein liegt bereits eine Anmeldung vor. "
                "Bei Fragen bitte den Veranstalter kontaktieren."
            )

    if fehler:
        formularbremse.fehlversuch(schluessel)
        return render_template(
            "anmeldung_form.html", tournament=tournament,
            offen=offen, grund=grund, infos=infos,
            daten=daten, fehler=fehler,
        ), 400

    # Ist die Anmeldung geschlossen, landet man auf der Warteliste statt im
    # Nirgendwo – ausser der Veranstalter hat das Formular ganz abgeschaltet.
    if not offen and (get_setting(tournament.id, "registration_open") != "1"):
        flash(grund or "Die Anmeldung ist nicht geöffnet.", "error")
        return render_template(
            "anmeldung_form.html", tournament=tournament,
            offen=False, grund=grund, infos=infos, daten=daten, fehler={},
        ), 403

    status = ANMELDUNG_OFFEN if offen else ANMELDUNG_WARTELISTE
    anmeldung = Registration(
        tournament_id=tournament.id,
        club_name=daten["club_name"],
        team_name=daten["team_name"],
        contact_name=daten["contact_name"],
        contact_email=daten["contact_email"],
        contact_phone=daten["contact_phone"],
        player_count=daten["player_count"],
        notes=daten["notes"],
        status=status,
    )
    db.session.add(anmeldung)
    db.session.commit()
    formularbremse.fehlversuch(schluessel)   # zaehlt auch erfolgreiche Sendungen

    return render_template("anmeldung_danke.html", tournament=tournament,
                           anmeldung=anmeldung, honeypot=False)


@anmeldung_bp.route("/t/<slug>/anmeldung/status/<token>")
def anmeldestatus_seite(slug, token):
    """Statusseite fuer den Verein – erreichbar nur mit dem Token."""
    tournament = _turnier_oder_404(slug)
    g.tournament = tournament
    anmeldung = Registration.query.filter_by(
        tournament_id=tournament.id, token=token).first()
    if not anmeldung:
        abort(404)
    return render_template("anmeldung_status.html", tournament=tournament,
                           anmeldung=anmeldung)


@anmeldung_bp.route("/t/<slug>/anmeldung/status/<token>/zurueckziehen",
                    methods=["POST"])
def anmeldung_zurueckziehen(slug, token):
    """Der Verein zieht seine Anmeldung selbst zurueck."""
    tournament = _turnier_oder_404(slug)
    anmeldung = Registration.query.filter_by(
        tournament_id=tournament.id, token=token).first()
    if not anmeldung:
        abort(404)

    if anmeldung.status == ANMELDUNG_BESTAETIGT:
        flash("Die Anmeldung ist schon bestätigt und im Spielplan. Bitte "
              "wende dich direkt an den Veranstalter.", "error")
        return redirect(url_for("anmeldung.anmeldestatus_seite",
                                slug=slug, token=token))

    anmeldung.status = ANMELDUNG_ABGELEHNT
    anmeldung.decision_note = "Vom Verein selbst zurückgezogen."
    anmeldung.decided_at = datetime.now(timezone.utc)
    db.session.commit()
    flash("Die Anmeldung wurde zurückgezogen.", "success")
    return redirect(url_for("anmeldung.anmeldestatus_seite",
                            slug=slug, token=token))


# ──────────────────────────────────────
# Adminbereich
# ──────────────────────────────────────

anmeldung_admin_bp = Blueprint("anmeldung_admin", __name__)


@anmeldung_admin_bp.route("/t/<slug>/anmeldungen")
@login_required
@tournament_required
def liste():
    t = g.tournament
    status_filter = request.args.get("status", "")
    query = Registration.query.filter_by(tournament_id=t.id)
    if status_filter in ANMELDUNG_STATUS:
        query = query.filter_by(status=status_filter)
    anmeldungen = query.order_by(Registration.created_at.desc()).all()

    gruppen = Group.query.filter_by(tournament_id=t.id).order_by(
        Group.display_order, Group.name).all()
    offen, grund, infos = anmeldestatus(t.id)

    return render_template(
        "admin/anmeldungen.html",
        tournament=t,
        anmeldungen=anmeldungen,
        zahlen=anmeldungen_zaehlen(t.id),
        gruppen=gruppen,
        status_filter=status_filter,
        anmeldung_offen=offen,
        anmeldung_grund=grund,
        infos=infos,
        einstellungen=get_all_settings(t.id),
    )


@anmeldung_admin_bp.route("/t/<slug>/api/anmeldungen/einstellungen",
                          methods=["POST"])
@login_required
@editor_required
@tournament_required
def einstellungen_speichern():
    t = g.tournament
    daten = request.get_json(silent=True) or request.form

    set_setting(t.id, "registration_open",
                "1" if str(daten.get("registration_open")) in ("1", "true", "on") else "0")

    frist = (daten.get("registration_deadline") or "").strip()
    if frist:
        try:
            date.fromisoformat(frist)
        except ValueError:
            return jsonify({"error": "Frist muss ein Datum sein (JJJJ-MM-TT)."}), 400
    set_setting(t.id, "registration_deadline", frist)

    max_teams = (daten.get("registration_max_teams") or "").strip()
    if max_teams:
        try:
            if int(max_teams) < 0:
                raise ValueError
        except ValueError:
            return jsonify({"error": "Maximale Teamzahl muss eine Zahl sein."}), 400
    set_setting(t.id, "registration_max_teams", max_teams)

    set_setting(t.id, "registration_fee",
                (daten.get("registration_fee") or "").strip()[:20])
    set_setting(t.id, "registration_info",
                (daten.get("registration_info") or "").strip()[:2000])

    if request.is_json:
        return jsonify({"ok": True})
    flash("Anmelde-Einstellungen gespeichert.", "success")
    return redirect(url_for("anmeldung_admin.liste", slug=t.slug))


def _anmeldung_oder_404(aid):
    t = g.tournament
    anmeldung = db.session.get(Registration, aid)
    if not anmeldung or anmeldung.tournament_id != t.id:
        abort(404)
    return anmeldung


@anmeldung_admin_bp.route("/t/<slug>/anmeldungen/<int:aid>/bestaetigen",
                          methods=["POST"])
@login_required
@editor_required
@tournament_required
def bestaetigen(aid):
    """Anmeldung annehmen und daraus ein Team im Spielplan machen."""
    t = g.tournament
    anmeldung = _anmeldung_oder_404(aid)

    if anmeldung.status == ANMELDUNG_BESTAETIGT and anmeldung.team_id:
        flash("Diese Anmeldung ist bereits bestätigt.", "error")
        return redirect(url_for("anmeldung_admin.liste", slug=t.slug))

    teamname = (request.form.get("team_name") or "").strip() or anmeldung.anzeige_teamname
    if Team.query.filter_by(tournament_id=t.id, name=teamname).first():
        flash(f"Es gibt bereits ein Team '{teamname}'. Bitte beim Bestätigen "
              "einen anderen Namen vergeben.", "error")
        return redirect(url_for("anmeldung_admin.liste", slug=t.slug))

    gruppe_id = request.form.get("group_id", type=int)
    if gruppe_id:
        gruppe = db.session.get(Group, gruppe_id)
        if not gruppe or gruppe.tournament_id != t.id:
            gruppe_id = None

    team = Team(
        tournament_id=t.id,
        name=teamname,
        group_id=gruppe_id or None,
        players="",
    )
    db.session.add(team)
    db.session.flush()

    # Startgebuehr als offener Posten anlegen, damit sie in der
    # Organisation-Ansicht auftaucht
    gebuehr = (get_setting(t.id, "registration_fee") or "").strip()
    betrag = None
    if gebuehr:
        try:
            betrag = float(gebuehr.replace(",", "."))
        except ValueError:
            betrag = None
    db.session.add(TeamPayment(team_id=team.id, paid=False, amount=betrag))

    anmeldung.status = ANMELDUNG_BESTAETIGT
    anmeldung.team_id = team.id
    anmeldung.decided_at = datetime.now(timezone.utc)
    anmeldung.decided_by = current_user.id
    anmeldung.decision_note = (request.form.get("note") or "").strip()
    db.session.commit()
    broadcast_state(t.id)

    flash(f"'{anmeldung.club_name}' bestätigt – Team '{teamname}' angelegt.",
          "success")
    return redirect(url_for("anmeldung_admin.liste", slug=t.slug))


def _status_setzen(aid, neuer_status, meldung):
    t = g.tournament
    anmeldung = _anmeldung_oder_404(aid)
    anmeldung.status = neuer_status
    anmeldung.decided_at = datetime.now(timezone.utc)
    anmeldung.decided_by = current_user.id
    anmeldung.decision_note = (request.form.get("note") or "").strip()
    db.session.commit()
    flash(meldung.format(verein=anmeldung.club_name), "success")
    return redirect(url_for("anmeldung_admin.liste", slug=t.slug))


@anmeldung_admin_bp.route("/t/<slug>/anmeldungen/<int:aid>/ablehnen",
                          methods=["POST"])
@login_required
@editor_required
@tournament_required
def ablehnen(aid):
    return _status_setzen(aid, ANMELDUNG_ABGELEHNT, "'{verein}' abgelehnt.")


@anmeldung_admin_bp.route("/t/<slug>/anmeldungen/<int:aid>/warteliste",
                          methods=["POST"])
@login_required
@editor_required
@tournament_required
def warteliste(aid):
    return _status_setzen(aid, ANMELDUNG_WARTELISTE,
                          "'{verein}' auf die Warteliste gesetzt.")


@anmeldung_admin_bp.route("/t/<slug>/anmeldungen/<int:aid>/zuruecksetzen",
                          methods=["POST"])
@login_required
@editor_required
@tournament_required
def zuruecksetzen(aid):
    """Entscheidung zurueckholen. Ein bereits angelegtes Team bleibt bestehen."""
    t = g.tournament
    anmeldung = _anmeldung_oder_404(aid)
    anmeldung.status = ANMELDUNG_OFFEN
    anmeldung.decided_at = None
    anmeldung.decided_by = None
    anmeldung.decision_note = ""
    db.session.commit()
    flash(f"'{anmeldung.club_name}' wieder als offen markiert. "
          "Ein bereits angelegtes Team wurde nicht gelöscht.", "success")
    return redirect(url_for("anmeldung_admin.liste", slug=t.slug))


@anmeldung_admin_bp.route("/t/<slug>/anmeldungen/<int:aid>/loeschen",
                          methods=["POST"])
@login_required
@superadmin_required
@tournament_required
def loeschen(aid):
    t = g.tournament
    anmeldung = _anmeldung_oder_404(aid)
    name = anmeldung.club_name
    db.session.delete(anmeldung)
    db.session.commit()
    flash(f"Anmeldung von '{name}' gelöscht. Ein daraus entstandenes Team "
          "bleibt im Spielplan.", "success")
    return redirect(url_for("anmeldung_admin.liste", slug=t.slug))


@anmeldung_admin_bp.route("/t/<slug>/anmeldungen/export.csv")
@login_required
@tournament_required
def export_csv():
    """Anmeldeliste als CSV – fuer Serienbriefe, Excel, Verbandsmeldungen."""
    t = g.tournament
    anmeldungen = Registration.query.filter_by(tournament_id=t.id).order_by(
        Registration.created_at).all()

    puffer = io.StringIO()
    # Semikolon: Excel in deutscher Spracheinstellung erwartet das
    writer = csv.writer(puffer, delimiter=";")
    writer.writerow([
        "Verein", "Teamname", "Ansprechpartner", "E-Mail", "Telefon",
        "Spieleranzahl", "Status", "Anmerkungen", "Eingegangen am",
        "Entschieden am", "Notiz",
    ])
    for a in anmeldungen:
        writer.writerow([
            a.club_name, a.anzeige_teamname, a.contact_name,
            a.contact_email, a.contact_phone or "",
            a.player_count if a.player_count else "",
            a.status_label, (a.notes or "").replace("\n", " "),
            a.created_at.strftime("%d.%m.%Y %H:%M") if a.created_at else "",
            a.decided_at.strftime("%d.%m.%Y %H:%M") if a.decided_at else "",
            (a.decision_note or "").replace("\n", " "),
        ])

    # BOM, damit Excel die Umlaute richtig liest
    inhalt = "﻿" + puffer.getvalue()
    antwort = current_app.response_class(inhalt, mimetype="text/csv")
    antwort.headers["Content-Disposition"] = (
        f'attachment; filename="anmeldungen-{t.slug}.csv"'
    )
    return antwort
