"""Blueprint-Objekte an einer Stelle.

Damit koennen sich mehrere Module Routen am selben Blueprint registrieren,
ohne sich gegenseitig zu importieren (und damit ohne Importzyklus).
"""
from flask import Blueprint

admin_bp = Blueprint("admin", __name__, template_folder="templates")
