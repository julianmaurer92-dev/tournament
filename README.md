# Jugendfussballturnier – Live-Webapp

Webapp zur Verwaltung und Live-Anzeige eines Jugendfuballturniers mit Gruppenphase.

## Features

- **Live-Ansicht**: Aktuelles Spiel mit Ergebnis, LIVE-Badge und Countdown-Timer
- **Gruppen-System**: Mehrere Gruppen (z.B. Gruppe A, B, C) mit eigenen Tabellen
- **Gruppen-Tabs**: Wechsel zwischen Gruppen per Klick im Frontend
- **Tabelle pro Gruppe**: Automatische Berechnung (Punkte, Tordifferenz, Tore)
- **Echtzeit-Updates**: WebSocket-basiert, kein Seitenreload noetig
- **Admin-Bereich**: Gruppen, Teams, Spiele verwalten + Timer-Steuerung
- **Drag & Drop**: Spielreihenfolge per Drag & Drop im Admin anpassen
- **Design-Einstellungen**: Turniername, Primaerfarbe, Sekundaerfarbe und Titelfarbe live anpassbar
- **Live-Vorschau**: Farbaenderungen werden sofort im Admin-Preview und auf allen Clients angezeigt
- **Responsives Design**: Optimiert fuer TV, Tablet, Desktop (dunkles Theme mit CSS Custom Properties)

## Schnellstart

```bash
cd tournament
docker-compose up --build
```

Die App ist erreichbar unter: **http://localhost:5000**

### Admin-Zugang

- URL: http://localhost:5000/admin
- Benutzername: `admin`
- Passwort: `admin123`

## Konfiguration

Umgebungsvariablen in `docker-compose.yml`:

| Variable         | Standard                            | Beschreibung     |
|------------------|-------------------------------------|------------------|
| `SECRET_KEY`     | `change-me-in-production-please`    | Flask Secret Key |
| `ADMIN_PASSWORD` | `admin123`                          | Admin-Passwort   |
| `DATABASE_URL`   | `sqlite:////app/data/tournament.db` | Datenbank-Pfad   |

## Ablauf

1. **Gruppen anlegen**: Admin > Gruppen > z.B. "Gruppe A", "Gruppe B"
2. **Teams anlegen**: Admin > Mannschaften > Teamname + Gruppe zuweisen
3. **Spiele erstellen**: Admin > Spiele > Teams + Gruppe + Spieldauer waehlen
4. **Spielreihenfolge anpassen**: Im Dashboard per Drag & Drop die Spiele sortieren
5. **Spiel steuern**: "Steuerung" klicken > Timer starten, Tore per +/- eintragen
6. **Design anpassen**: Admin > Design > Farben und Turniername aendern
7. **Live-Ansicht**: Hauptseite zeigt Live-Spiel, Gruppen-Tabs fuer Tabelle/Spiele

## Design-Einstellungen

Ueber **Admin > Design** koennen folgende Einstellungen live angepasst werden:

| Einstellung    | Beschreibung                                       | Standard    |
|----------------|----------------------------------------------------|-------------|
| Turniername    | Wird im Header der Live-Ansicht angezeigt          | JUGENDFUSSBALLTURNIER |
| Titelfarbe     | Schriftfarbe des Turniernamens                     | `#22c55e`   |
| Primaerfarbe   | Akzentfarbe fuer Buttons, Badges, aktive Elemente  | `#22c55e`   |
| Sekundaerfarbe | Hintergrund fuer Panels und Karten                 | `#1a2332`   |

Aenderungen werden sofort per WebSocket an alle verbundenen Clients uebertragen.

## Datenmodell

- **Group**: id, name, display_order
- **Team**: id, name, logo_url, players, group_id (FK)
- **Match**: id, team1_id, team2_id, group_id, score, status, timer_state, match_order
- **Admin**: id, username, password_hash
- **Settings**: key, value (Key-Value-Store fuer Turniername + Farben)

## Projektstruktur

```
tournament/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── run.py
└── app/
    ├── __init__.py          # Flask app factory + settings context processor
    ├── models.py            # SQLAlchemy models + standings calc + settings helpers
    ├── routes.py            # Public routes + API
    ├── admin.py             # Admin CRUD + match control + reorder + design API
    ├── socket_events.py     # WebSocket broadcast with settings
    ├── static/
    │   ├── css/style.css    # Dark theme, CSS custom properties, responsive
    │   └── js/main.js       # WebSocket client, group tabs, timer, dynamic theming
    └── templates/
        ├── base.html            # Dynamic CSS custom properties from DB
        ├── index.html           # Public 3-column view
        └── admin/
            ├── login.html
            ├── dashboard.html       # Drag & Drop Spielreihenfolge
            ├── design.html          # Farbpicker + Live-Vorschau
            └── match_control.html
```

## Lokale Entwicklung (ohne Docker)

```bash
pip install -r requirements.txt
python run.py
```
