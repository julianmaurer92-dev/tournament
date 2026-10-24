"""Gemeinsame Werte und Helfer fuer die Browser-Tests.

Diese Tests laufen gegen die laufende Dev-Instanz (Service "web" im
Compose-Projekt cupplan-dev), nicht gegen eine eigene Datenbank. Sie sind
damit die einzige Teststufe, die wirklich sieht, was im Browser passiert:
ob JavaScript Fehler wirft, ob Socket.IO verbindet, ob eine Seite leer
bleibt.

Starten:
    docker compose -p cupplan-dev -f docker-compose.dev.yml run --rm e2e
"""
import os
import re

BASIS = os.environ.get("CUPPLAN_BASE_URL", "http://web:5000")
ADMIN = os.environ.get("CUPPLAN_ADMIN_USER", "admin")
PASSWORT = os.environ.get("CUPPLAN_ADMIN_PASSWORD", "admin123")

ERGEBNISSE = "/work/test-results"

# Meldungen, die der Browser von sich aus produziert und die nichts mit
# unserem Code zu tun haben.
HARMLOSE_MELDUNGEN = (
    "favicon",
    "Failed to load resource",     # fehlende Logos in Testdaten
    "net::ERR_",                   # Schriften/CDN ohne Internet im Container
    "fonts.googleapis",
    "fonts.gstatic",
    "cdn.jsdelivr",
    "cdnjs.cloudflare",
)


def ist_harmlos(text):
    return any(teil in text for teil in HARMLOSE_MELDUNGEN)


def bild(seite, name):
    """Screenshot ablegen – landet in ./test-results/ auf dem Host."""
    os.makedirs(ERGEBNISSE, exist_ok=True)
    seite.screenshot(path=f"{ERGEBNISSE}/{name}.png", full_page=True)
