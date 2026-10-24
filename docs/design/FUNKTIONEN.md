# Funktionsinventar

Stand: 24.10.2026, 20:15 Uhr · Branch `ui/neues-design`

Diese Liste ist die Prüfliste für das Redesign. **Jede Zeile muss am Ende
erreichbar sein und funktionieren** – egal wie die Oberfläche aussieht.
Abgehakt wird erst, wenn die Funktion im neuen Gewand nachweislich geht.

Erhoben aus `app.url_map` (113 Routen, ohne statische Dateien), nicht aus
den Vorlagen – so fällt nichts durch, was nur über eine Schaltfläche
irgendwo tief in einer Seite erreichbar ist.

---

## Öffentlich (ohne Anmeldung)

| Seite | Route | Was man dort tut |
|---|---|---|
| Startseite | `/` | Turniere des Wochenendes wählen, zur Speisekarte |
| Speisekarte | `/speisekarte` | Speisen und Getränke mit Preisen lesen |
| Live-Ansicht | `/t/<slug>/` | Ankündigung, laufendes Spiel, Ergebnisse, Gruppentabellen, am Ende Podium |
| Handy-Ansicht | `/t/<slug>/phone/` | dasselbe in Reitern: Live, Tabelle, Spiele, Finals, Teams, Bestimmungen |
| Beamer-Ansicht | `/t/<slug>/tv/` | Uhr, Tabellen, Ergebnisse, Platzierungen – aus Entfernung lesbar |
| Turnierauswahl Handy | `/t/` | Liste der Turniere, für kleine Bildschirme |
| Turnierauswahl Beamer | `/tv/` | dasselbe für den Beamer |
| Speisekarte Handy / Beamer | `/phone/speisekarte`, `/tv/speisekarte` | eigene Fassungen |
| Statistik | `/t/<slug>/statistik` | Torschützenliste, Fair-Play-Wertung |
| Endplatzierung | `/t/<slug>/platzierung` | Abschlusstabelle nach dem Turnier |
| Vereinsanmeldung | `/t/<slug>/anmeldung` | Formular: Verein meldet eine Mannschaft an |
| Anmeldestatus | `/t/<slug>/anmeldung/status/<token>` | Stand einsehen, Anmeldung zurückziehen |

**Datenschnittstellen** (werden von den Ansichten per Socket.IO/Abruf genutzt):
`/t/<slug>/api/state`, `/api/statistik`, `/api/platzierung`.

---

## Adminbereich

### Einstieg

| Funktion | Route |
|---|---|
| Anmelden (Benutzer/Passwort) | `/admin/login` |
| Anmelden über Google | `/admin/login/google` |
| Abmelden | `/admin/logout` |

### Turniere

| Funktion | Route |
|---|---|
| Turnierliste | `/admin/` |
| Turnier anlegen | `POST /admin/tournaments` |
| Turnier bearbeiten (Name, Datum, Uhrzeit, Beschreibung, Finalrundentyp) | `POST /admin/tournaments/<tid>/edit` |
| Turnier löschen | `POST /admin/tournaments/<tid>/delete` |

### Turnier-Übersicht (Dashboard) `/admin/t/<slug>/`

- Turnierphase anzeigen und umschalten: Gruppenphase beenden, Finalrunde
  starten, vorhandene Finals verwenden, ohne Finalrunde abschließen,
  Turnier beenden, Phase zurücksetzen, **Vollständiger Reset**
- Ankündigung schreiben und senden, Ankündigung löschen
- Gruppentabellen live
- Gruppenspiele und Finalspiele als Liste, Reihenfolge per Ziehen
- Nächste Spiele starten (ein oder zwei Felder gleichzeitig)
- Zur Spielsteuerung springen
- Heim und Gast tauschen
- Spielfeld eines Spiels setzen
- Gruppenspiele simulieren (Testhilfe)
- Gesamtrangliste abrufen

### Spielsteuerung `/admin/t/<slug>/matches/<mid>/control`

Das Herzstück am Turniertag:

- Ergebnis erhöhen und verringern (beide Mannschaften)
- **Tor mit Torschütze** eintragen, Ereignis wieder löschen
- Karten eintragen (gelb, gelb-rot, rot)
- Timer: starten, anhalten, zurücksetzen, Zeit setzen
- Verlängerung starten
- Elfmeterschießen kennzeichnen
- Spielstatus setzen (geplant, läuft, beendet)
- Ankündigung „Nächstes Spiel" auslösen
- Ereignisliste des Spiels ansehen

### Turnieradministration `/admin/t/<slug>/administration`

- Stammdaten, Finalrundentyp, Spielfelder, Spielzeit, Verlängerung
- Was Zuschauer sehen (Tabelle/Ergebnisse verbergen)
- Turnierbestimmungen schreiben
- **Gruppen**: anlegen, umbenennen, löschen
- **Teams**: anlegen, bearbeiten (Name, Gruppe, Wappen, Spieler), löschen,
  CSV-Import
- **Spiele**: anlegen, löschen, alle löschen, Reihenfolge ändern,
  Jeder-gegen-jeden erzeugen, CSV-Import, Terminkonflikte prüfen
- Phasen-Resets

### Weitere Turnierseiten

| Seite | Route | Funktionen |
|---|---|---|
| Finalrunde einrichten | `/admin/t/<slug>/finals-setup` | Paarungen festlegen, Reihenfolge |
| Schiedsrichter | `/admin/t/<slug>/schiedsrichter` | anlegen, bearbeiten, löschen, automatisch verteilen, Konflikte, Einsatzplan + CSV |
| Statistik | `/admin/t/<slug>/statistik` | Torschützen, Karten, CSV-Export |
| Siegerehrung | `/admin/t/<slug>/siegerehrung` | Platzierungen, Urkundentexte, CSV, Urkunden drucken |
| Organisation | `/admin/t/<slug>/organisation` | Startgebühr, bezahlt/offen je Mannschaft, Quittung einzeln und alle, Logo und Bezeichnung |
| Anmeldungen | `/admin/t/<slug>/anmeldungen` | bestätigen, ablehnen, Warteliste, zurücksetzen, löschen, CSV, Anmeldung öffnen/schließen, Frist, Höchstzahl, Gebühr, Infotext |
| Design | `/admin/t/<slug>/design` | Theme, Hell/Dunkel, Vereinsfarbe, Anzeige |
| Spielplan drucken | `/admin/t/<slug>/schedule/print` | Aushang |
| Kabinenschilder | `/admin/t/<slug>/cabin-signs` | Türschilder je Mannschaft |
| Urkunden | `/admin/t/<slug>/urkunden` | Druckansicht |

### Übergreifend

| Seite | Route | Funktionen |
|---|---|---|
| Benutzer | `/admin/users` | anlegen, bearbeiten (Rolle, Passwort, Turnierzugriff), löschen |
| Speisekarte | `/admin/speisekarte` | anlegen, bearbeiten, löschen, CSV-Import, Mehrfachlöschen, Reihenfolge |
| Export/Import | `/admin/export-import` | alles als JSON sichern und zurückspielen |

---

## Was der Auftrag nennt, aber im Repository nicht existiert

Drei Punkte aus der Aufgabenbeschreibung haben **keine Route im Code**:

| Genannt | Befund |
|---|---|
| Sponsoren-Verwaltung | kein `/admin/sponsors`, kein Modell, keine Vorlage |
| SMTP-Konfiguration | kein `/admin/smtp-settings`; es gibt nur die Einstellungsschlüssel |
| Mobil-Ansicht (App-artig mit Bottom-Navigation) | kein `/t/<slug>/mobile/`; es gibt `/t/<slug>/phone/` |

Da laut Auftrag **ausschließlich der Code maßgeblich** ist und das Backend
unverändert bleiben soll, baue ich diese drei nicht neu – das wären neue
Fachfunktionen, keine Gestaltung.

**Aber:** Die „Mobil-Ansicht mit Bottom-Navigation" ist eine reine
Gestaltungsfrage. Die Handy-Ansicht bekommt im neuen Design genau das –
eine App-artige Leiste unten. Damit ist der Wunsch erfüllt, ohne eine
neue Route zu erfinden.

---

## Prüfstand

| | |
|---|---|
| Routen gesamt (ohne statische) | 113 |
| davon Seiten (GET, HTML) | 44 |
| davon Aktionen (POST) | 64 |
| Bestehende Tests | 508 |

Abgehakt wird in `DESIGN_LOG.md` → „Funktionsabgleich".
