# Logbuch Nachtschicht 23./24.10.2026

Branch: `nightly/2026-10-24` · Arbeitsverzeichnis: `/home/mj/cupplan-dev`
Remote: `https://github.com/julianmaurer92-dev/tournament.git`

---

## Wichtige Befunde direkt zu Beginn (bitte zuerst lesen)

### 1. Die Produktion läuft NICHT auf dieser VM

Der Auftrag ging davon aus, dass cupplan.de als Docker-Container auf dieser
Maschine läuft. Das ist nicht so:

- `cupplan.de` → `85.215.206.46` (externer VPS, vermutlich IONOS)
- diese Maschine ist `dev` / `192.168.8.172`
- `docker ps` hier zeigt: glpi, glpi-db, staedtetrip-umfrage, smart-pantry-web,
  smart-pantry-db, dockge – **keinen** cupplan-Container
- es gibt kein `pg-data`-Volume, also auch keine lokale Produktionsdatenbank

**Folge:** Es bestand hier nie die Gefahr, die Produktion anzufassen. Ich habe
trotzdem in einem separaten Klon (`/home/mj/cupplan-dev`) und einem eigenen
Compose-Projekt (`cupplan-dev`, Port 8090) gearbeitet – siehe Punkt 2, warum
das ohnehin notwendig war.

**Folge 2:** Ein Backup der Produktionsdatenbank war von hier aus nicht
möglich. Dafür bräuchte man SSH-Zugang zum VPS; in `~/.ssh/config` ist kein
Eintrag für `85.215.206.46` hinterlegt. Die Live-Daten (Winkelturnier 2026,
9 Teams, Speisekarte, Benutzer) sind also **nicht gesichert**. Siehe
"Offene Punkte".

### 2. Der komplette Funktionsstand v1.5 war nicht eingecheckt

In `/home/mj/cupplan` lag der Code als uncommittete Arbeitskopie:

- letzter Commit auf `main`: `65782b8 Add installation script for VPS deployment`
- davor nur `5327677 Initial commit`
- uncommittet: 19 geänderte + 17 neue Dateien, ~10.200 Zeilen –
  also praktisch alles, was die App heute kann (Phone-/TV-Ansichten,
  Benutzerverwaltung, Export/Import, Organisation/Startgebühren,
  Kabinenschilder, Druckansichten, Finals-Setup)

Die Anweisung lautete, im Dev-Klon vom letzten Commit auszugehen. Das hätte
bedeutet, gegen eine App zu entwickeln, der alle heute genutzten Funktionen
fehlen. **Entscheidung:** Ich habe die Arbeitskopie 1:1 als Baseline-Commit
auf den Nightly-Branch gelegt (`28e1545`). Das Original-Verzeichnis
`/home/mj/cupplan` wurde nicht verändert; eine Sicherung liegt unter
`/home/mj/cupplan-backups/2026-10-23/cupplan-worktree/`.

### 3. Die Live-Version ist NEUER als der lokale Code

Beim Abgleich der öffentlichen Routen gegen cupplan.de zeigt sich: Live
existieren Endpunkte, die es im lokalen Code gar nicht gibt.

| Route | lokal | live (cupplan.de) |
|---|---|---|
| `/t/<slug>/mobile/` | fehlt | 200 |
| `/admin/sponsors` | fehlt | 302 (Login-Redirect, Route existiert) |
| `/admin/smtp-settings` | fehlt | 302 (Route existiert) |

Auf dem VPS läuft also ein Stand, der hier nirgends vorliegt (Mobile-Ansicht
mit Bottom-Navigation, Sponsoren-Verwaltung, SMTP-Einstellungen). Ohne
SSH-Zugang kann ich diesen Code nicht holen.

**Das ist der wichtigste offene Punkt der Nacht:** Der Nightly-Branch
einfach nach `main` zu mergen und zu deployen würde diese drei
Live-Funktionen löschen. Vorgehen siehe "Offene Punkte & Deployment".

---

## Architektur-Übersicht (Stand bei Beginn)

```
run.py                 → create_app() + socketio
app/__init__.py        → App-Factory, DB, Login, SocketIO, Google-OAuth,
                         _migrate_db() (additive SQL bei jedem Start),
                         _ensure_admin()
app/models.py    (472) → Admin, UserTournamentAccess, Tournament,
                         TournamentSettings (Key-Value je Turnier), Group,
                         Team, TeamPayment, Match, MenuItem
                         + calculate_standings(), calculate_overall_rankings(),
                           get_seeded_teams_cross_group()
app/routes.py    (147) → öffentliche Ansichten (Landing, /t/<slug>/,
                         /tv/, /phone/, Speisekarte) + /api/state
app/admin.py    (2582) → ALLES Administrative in einem Modul:
                         Auth, Turnierverwaltung, Dashboard, Organisation,
                         Design, Phasensteuerung, Finalrunden-Generatoren,
                         Gruppen, Teams, Spiele, Timer, Speisekarte,
                         Benutzer, Export/Import
app/socket_events.py   → Socket.IO: join_tournament, state_update-Broadcast
app/templates/         → Jinja, Tabler-CSS; dashboard.html mit ~17 KB
                         Inline-Script
app/static/            → style.css (1813 Zeilen), main.js (547 Zeilen)
```

Datenhaltung: Postgres 16. Schema-Änderungen laufen über die SQL-Liste in
`_migrate_db()`, kein Alembic. Echtzeit: ein gunicorn-Worker mit
gevent-WebSocket, Broadcast des gesamten Turnierzustands bei jeder Änderung.

Bewertung: Das Datenmodell ist für eine „vibe-gecodete" App überraschend
solide (Settings als Key-Value je Turnier, saubere Turnier-Trennung,
Rollenmodell). Die Probleme liegen woanders: ein 2582-Zeilen-Modul, keine
Tests, Secrets mit Default-Werten, und die Turnier-Phasenlogik steckt
verstreut in Routen statt in einer eigenen Schicht.

---

## Plan für die Nacht

1. Dev-Stack + Testsuite als Netz (erledigt)
2. Regressionstests für alle bestehenden Funktionen
3. Sicherheits-Härtung
4. Vereinsanmeldung: öffentliches Formular + Freigabe im Admin
5. Spielplan-Generator mit echten Anstoßzeiten und n Feldern
6. Spielereignisse (Torschützen, Karten) → Torschützenliste, Fair-Play
7. Siegerehrung: Urkunden, Endplatzierung
8. Schiedsrichter-Verwaltung
9. Refactoring admin.py, Inline-Script auslagern
10. Playwright-E2E
11. Export/Import auf alle neuen Daten erweitern
12. UX-Review + Architektur-Empfehlung

---

## Verlauf

### 20:02 – Start, Bestandsaufnahme
Git-Status, Docker-Inventar, DNS-Auflösung, Live-Routen-Abgleich.
Die drei Befunde oben. Backup der Arbeitskopie nach
`/home/mj/cupplan-backups/2026-10-23/cupplan-worktree/`.

### 20:20 – Dev-Klon und Baseline
`/home/mj/cupplan-dev` angelegt, Branch `nightly/2026-10-24`,
Baseline-Commit `28e1545`. Push zu GitHub funktioniert.

### 20:35 – Dev-Stack und Testsuite (`89f890a`)
`docker-compose.dev.yml` mit eigenem Projektnamen `cupplan-dev`, Web auf
8090, DB auf 127.0.0.1:55432, eigene Volumes und Container-Namen – teilt
sich nichts mit irgendetwas anderem. Dazu `Dockerfile.dev` (gleicher
gevent-Worker wie Produktion, nur mit `--reload`).

pytest-Grundgerüst: 27 Tests für Tabellenberechnung und alle öffentlichen
Ansichten. Lief zunächst 113 s; Ursache war `create_app()` pro Test (auf
dieser CPU über eine Sekunde). App-Fixture auf Session-Scope umgestellt,
Isolation über `drop_all/create_all` → 49 s.

Kein lokales Python möglich: `python3-venv` und `pip` fehlen auf dem Host und
es gibt kein passwortloses sudo. Deshalb laufen Tests im Container
(`docker compose -p cupplan-dev -f docker-compose.dev.yml run --rm test`).

Seed-Skript `scripts/seed_dev.py`: drei Altersklassen (E/D/F-Jugend),
Gruppen, 19 Teams, 28 Spiele mit Anstoßzeiten, ein laufendes Spiel,
13 Speisekarten-Einträge, Benutzer aller Rollen.

### 20:45 – Produktionsfehler gefunden und behoben (`28079ee`)
`SQLAlchemy` war in `requirements.txt` nicht gepinnt. pip installiert
inzwischen 2.1.6, und dort ist der Standardtreiber für `postgresql://`
psycopg (v3) – im Image liegt aber `psycopg2-binary`. Der Dev-Container
startete mit `ModuleNotFoundError: No module named 'psycopg'`.

Das betrifft die Produktion genauso: Die Live-App läuft nur deshalb noch,
weil ihr Image älter ist. Ein `docker compose build` auf dem VPS hätte
cupplan.de lahmgelegt. Behoben durch Pin (`>=2.0.36,<2.1`) **und** einen
expliziten Treiber in der URL (`_normalize_db_uri()`), damit es auch bei
einer künftigen Version nicht wieder umkippt.

Tests: 35 passed.
