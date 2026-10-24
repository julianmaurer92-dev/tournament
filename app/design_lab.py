"""Design-Labor – nur für die Entwicklung.

Zeigt dieselbe Bildschirmmaske in mehreren Gestaltungsrichtungen, damit
man sie nebeneinander ansehen und sich entscheiden kann. Die Seite hängt
an keiner echten Funktion und wird nur registriert, wenn
``CUPPLAN_DESIGN_LAB=1`` gesetzt ist – in einer normalen Installation
existiert die Route also gar nicht.

Nach der Entscheidung bleibt sie als Beleg stehen: Wer später fragt,
warum die Oberfläche so aussieht und nicht anders, kann die Alternativen
noch einmal nebeneinander sehen.
"""
from flask import Blueprint, render_template

design_lab_bp = Blueprint("design_lab", __name__, url_prefix="/design-lab")

RICHTUNGEN = {
    "tafel": {
        "name": "Tafel",
        "kurz": "Anzeigetafel als Bauprinzip",
        "idee": (
            "Jedes Element ist eine Tafel: kräftiger Rand, Beschriftungs-"
            "streifen oben, Inhalt in Tabellenziffern. Das Vorbild ist das "
            "einzige Objekt, das am Sportplatz wirklich jeder ohne "
            "Nachdenken liest – die Anzeigetafel."
        ),
    },
    "kreide": {
        "name": "Kreide",
        "kurz": "Spielfeldlinien als Gestaltungselement",
        "idee": (
            "Die Geometrie des Platzes trägt die Gestaltung: Mittelkreis, "
            "Strafraum, Kreidelinien auf Grün. Hell, grafisch, verspielt – "
            "näher an einem Vereinsplakat als an einer Verwaltungssoftware."
        ),
    },
    "kiosk": {
        "name": "Kiosk",
        "kurz": "Große Kacheln, warm, fehlerverzeihend",
        "idee": (
            "Wie die Tafel am Getränkestand: warmes Papierweiß, dicke "
            "abgerundete Kacheln, kräftige Schrift, farbig sortiert. "
            "Gebaut für Handschuhe, Sonne und Helfer, die die App zum "
            "ersten Mal sehen."
        ),
    },
}


@design_lab_bp.route("/")
def uebersicht():
    return render_template("design_lab/uebersicht.html", richtungen=RICHTUNGEN)


@design_lab_bp.route("/<richtung>")
def probe(richtung):
    daten = RICHTUNGEN.get(richtung)
    if not daten:
        return "Unbekannte Richtung", 404
    return render_template("design_lab/probe.html",
                           richtung=richtung, daten=daten,
                           richtungen=RICHTUNGEN)
