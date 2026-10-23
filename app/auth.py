"""Zugriffs-Decorators, gemeinsam genutzt von allen Admin-Modulen.

Lagen bisher in admin.py. Hier herausgezogen, damit neue Module (z. B.
app/anmeldung.py) sie verwenden koennen, ohne admin.py zu importieren.
"""
from functools import wraps

from flask import abort, g
from flask_login import current_user

from app.models import Tournament


def superadmin_required(f):
    """Only superadmins may access this route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "superadmin":
            abort(403)
        return f(*args, **kwargs)
    return decorated


def editor_required(f):
    """Editors and superadmins may access this route (not viewers)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role == "viewer":
            abort(403)
        return f(*args, **kwargs)
    return decorated


def tournament_required(f):
    """Load tournament from URL slug into g.tournament and check access."""
    @wraps(f)
    def decorated(*args, **kwargs):
        slug = kwargs.pop("slug")
        tournament = Tournament.query.filter_by(slug=slug).first()
        if not tournament:
            abort(404)
        if not current_user.has_tournament_access(tournament.id):
            abort(403)
        g.tournament = tournament
        g.tid = tournament.id
        return f(*args, **kwargs)
    return decorated
