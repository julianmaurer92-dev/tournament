"""Was ist als Nächstes zu tun? – Wegweiser für die Turnieradministration.

Ein neues Turnier braucht eine bestimmte Reihenfolge: Gruppen, Teams,
Spielplan, Finalrundentyp, Phase starten. Diese Reihenfolge steht nirgends;
die Administrationsseite zeigt alle Bereiche gleichwertig nebeneinander.
Beim ersten Turnier muss man sie raten.

Reine Logik ohne Datenbank: Der Aufrufer sammelt die Zahlen, diese Funktion
entscheidet. Dadurch einzeln testbar und ohne Flask verwendbar.
"""

# Schluessel -> (Ueberschrift, Erklaerung, Ziel)
# "ziel" ist ein Kuerzel, das die Vorlage in einen Link uebersetzt.
SCHRITTE = {
    "gruppen": ("Gruppen anlegen",
                "Ohne Gruppen lassen sich weder Teams zuordnen noch "
                "Spiele erzeugen. Zwei Gruppen sind der Normalfall.",
                "gruppen"),
    "teams": ("Mannschaften eintragen",
              "Entweder von Hand, per CSV-Import – oder du öffnest die "
              "Vereinsanmeldung und bestätigst die Anmeldungen.",
              "anmeldungen"),
    "teams_pro_gruppe": ("Mannschaften auf die Gruppen verteilen",
                         "Mindestens zwei Mannschaften je Gruppe, sonst gibt "
                         "es in dieser Gruppe kein Spiel.",
                         "teams"),
    "spielplan": ("Spielplan erzeugen",
                  "Jeder gegen jeden innerhalb der Gruppen, verteilt auf "
                  "Spielfelder und Anstoßzeiten.",
                  "spielplan"),
    "anstosszeiten": ("Anstoßzeiten ergänzen",
                      "Der Spielplan hat keine Uhrzeiten. Ohne sie fehlen "
                      "Zeiten im Aushang, in den Live-Ansichten und bei der "
                      "Schiedsrichter-Einteilung.",
                      "spielplan"),
    "konflikte": ("Doppelbelegungen im Spielplan beheben",
                  "Mindestens eine Mannschaft oder ein Spielfeld ist "
                  "zweimal gleichzeitig angesetzt.",
                  "spielplan"),
    "schiedsrichter": ("Schiedsrichter einteilen",
                       "Noch sind Spiele ohne Schiedsrichter. Die "
                       "automatische Einteilung füllt die Lücken.",
                       "schiedsrichter"),
    "spiele_austragen": ("Spiele austragen",
                         "Alles steht bereit. Über die Spielsteuerung "
                         "startest du das nächste Spiel.",
                         "steuerung"),
    "gruppenphase_beenden": ("Gruppenphase beenden",
                             "Alle Gruppenspiele sind beendet. Danach legst "
                             "du die Finalrunde fest.",
                             "phase"),
    "finalrunde": ("Finalrunde festlegen",
                   "Die Gruppenphase ist abgeschlossen. Wähle den "
                   "Finalrundentyp oder beende das Turnier ohne Finale.",
                   "finals"),
    "finalspiele": ("Finalspiele austragen",
                    "Die Finalrunde läuft.",
                    "steuerung"),
    "turnier_beenden": ("Turnier beenden",
                        "Alle Finalspiele sind durch. Danach steht die "
                        "Endplatzierung fest.",
                        "phase"),
    "siegerehrung": ("Siegerehrung vorbereiten",
                     "Endplatzierung, Ablaufliste und Urkunden stehen bereit.",
                     "siegerehrung"),
}


def naechster_schritt(zahlen):
    """Welcher Schritt steht als Nächstes an?

    zahlen: dict mit
        phase, gruppen, teams, teams_ohne_gruppe, gruppen_mit_zu_wenig_teams,
        gruppenspiele, gruppenspiele_offen, spiele_ohne_zeit, konflikte,
        schiedsrichter, spiele_ohne_schiedsrichter, finalspiele,
        finalspiele_offen

    Liefert (schluessel, ueberschrift, erklaerung, ziel) oder None, wenn
    nichts offen ist.
    """
    phase = zahlen.get("phase", "GROUP_STAGE")

    if phase == "FINISHED":
        return _bau("siegerehrung")

    if phase == "FINAL_ROUND":
        if zahlen.get("finalspiele_offen", 0) > 0:
            return _bau("finalspiele")
        return _bau("turnier_beenden")

    if phase == "FINAL_SETUP":
        return _bau("finalrunde")

    # ── Gruppenphase ──────────────────────────────────
    if zahlen.get("gruppen", 0) == 0:
        return _bau("gruppen")

    if zahlen.get("teams", 0) == 0:
        return _bau("teams")

    if zahlen.get("gruppen_mit_zu_wenig_teams", 0) > 0:
        return _bau("teams_pro_gruppe")

    if zahlen.get("gruppenspiele", 0) == 0:
        return _bau("spielplan")

    if zahlen.get("konflikte", 0) > 0:
        return _bau("konflikte")

    if zahlen.get("spiele_ohne_zeit", 0) > 0:
        return _bau("anstosszeiten")

    # Schiedsrichter sind freiwillig: nur erinnern, wenn welche angelegt sind
    if (zahlen.get("schiedsrichter", 0) > 0
            and zahlen.get("spiele_ohne_schiedsrichter", 0) > 0):
        return _bau("schiedsrichter")

    if zahlen.get("gruppenspiele_offen", 0) > 0:
        return _bau("spiele_austragen")

    return _bau("gruppenphase_beenden")


def _bau(schluessel):
    ueberschrift, erklaerung, ziel = SCHRITTE[schluessel]
    return {
        "schluessel": schluessel,
        "ueberschrift": ueberschrift,
        "erklaerung": erklaerung,
        "ziel": ziel,
    }


def _anzahl(wert, einzahl, mehrzahl):
    return f"{wert} {einzahl if wert == 1 else mehrzahl}"


def fortschritt(zahlen):
    """Kurzfassung des Stands für die Kopfzeile, z. B. für eine Statuszeile."""
    teile = []
    if zahlen.get("gruppen"):
        teile.append(_anzahl(zahlen["gruppen"], "Gruppe", "Gruppen"))
    if zahlen.get("teams"):
        teile.append(_anzahl(zahlen["teams"], "Mannschaft", "Mannschaften"))
    if zahlen.get("gruppenspiele"):
        offen = zahlen.get("gruppenspiele_offen", 0)
        gespielt = zahlen["gruppenspiele"] - offen
        teile.append(f"{gespielt}/{zahlen['gruppenspiele']} Gruppenspiele")
    if zahlen.get("finalspiele"):
        offen = zahlen.get("finalspiele_offen", 0)
        gespielt = zahlen["finalspiele"] - offen
        teile.append(f"{gespielt}/{zahlen['finalspiele']} Finalspiele")
    if zahlen.get("schiedsrichter"):
        teile.append(_anzahl(zahlen["schiedsrichter"],
                             "Schiedsrichter", "Schiedsrichter"))
    return " · ".join(teile) if teile else "Noch nichts angelegt"
