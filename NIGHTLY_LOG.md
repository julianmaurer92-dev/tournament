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

### 21:02 – Rollen, Rechte und ein Datenverlust im Backup (`e2eec28`)
30 Tests für Anmeldung, Rollen und Turnier-Zugang. Dabei systematisch
geprüft, ob eine Route ein Objekt aus einem fremden Turnier anfasst
(Insecure Direct Object Reference): **keine Lücke gefunden** – jede Route
mit ID in der URL vergleicht gegen `g.tournament.id`. Das ist für eine
vibe-gecodete App bemerkenswert und jetzt festgenagelt.

Dafür ein echter Fund im JSON-Export: `event_time`, `match.field`,
`match.is_penalty` und die kompletten `TeamPayment`-Zeilen fehlten.
Heißt: Nach einem Wiederherstellen lagen alle Spiele auf Feld 1 und die
Buchhaltung der Startgebühren war weg. Exportformat auf Version 2 gehoben,
Version 1 bleibt importierbar.

### 21:17 – Sicherheits-Härtung (`ad36ddb`)
Cookie: `HttpOnly`, `SameSite=Lax`, `Secure` (im Dev-Modus aus).
`SameSite=Lax` ist hier die wirksamste Einzelmaßnahme – Browser senden das
Cookie dann nicht bei POST von fremden Seiten, womit die Admin-Formulare
gegen CSRF geschützt sind, obwohl es keine Token gibt. Echte Token betreffen
~40 Routen und jeden `fetch()`; bewusst nicht nachts angefangen.

Anmeldebremse: 8 Fehlversuche je Benutzer+IP, dann 5 Minuten Sperre (429).
Konfigurationswarnungen für Vorgabe-`SECRET_KEY`/`ADMIN_PASSWORD` ins Log und
als Banner für Superadmins – **bewusst kein Startabbruch**: Die App läuft auf
einem Turnier, ein verweigerter Start wäre schlimmer als die Warnung.

Zwei Fehler in meinen eigenen Fixtures behoben: die session-weite App behielt
Config-Änderungen einzelner Tests, und der offene App-Kontext ließ
Flask-Login seinen `current_user`-Cache in `g` über alle Anfragen eines
Tests teilen (ein Test als Superadmin und dann als Viewer sah zweimal den
Superadmin).

### 21:40 – Vereinsanmeldung (`45f1b7e`)
Das größte Stück: öffentliches Formular je Turnier, Statusseite mit Token,
Selbst-Zurückziehen, Warteliste bei Ausbuchung oder abgelaufener Frist.
Im Admin: Freigabe in einem Schritt zum Team (mit Gruppe und Startgebühr als
offenem Posten), Ablehnen, Warteliste, CSV-Export mit Semikolon und BOM.
Spamschutz per Honeypot und IP-Bremse, keine Captchas.

Entscheidung: `Registration` bewusst getrennt von `Team`. Eine Anmeldung ist
ein Antrag mit Kontaktdaten und Entscheidungshistorie, ein Team ist ein
Teilnehmer im Spielplan. Sonst verschmutzen abgelehnte Anmeldungen den
Spielplan.

Nebenbei: Zugriffs-Decorators nach `app/auth.py` gezogen.

### 22:10 – Spielplaner und zwei Löschfehler (`611675f`)
Der alte Generator mischte zufällig und verteilte mit `nummer % felder` –
keine Anstoßzeiten, und dieselbe Mannschaft konnte gleichzeitig auf Feld 1
und 2 antreten. Die neue Prüffunktion hat das sofort in meinen eigenen
Seed-Daten gefunden (2–4 Konflikte je Turnier).

Neu: `app/spielplan.py` als reine Logik – Slots, Felder, Mindestpause je
Mannschaft (wird gelockert statt zu scheitern), Anstoßzeiten mit optionaler
Mittagspause, Konfliktprüfung für bestehende Pläne. Dazu ein Dialog in der
Oberfläche und bis zu 6 Spielfelder statt 1 oder 2 (dafür musste die Annahme
„num_fields == '2' heißt mehrere Felder" an neun Stellen umgestellt werden).

Beim Umstellen des Seed-Skripts fielen zwei Löschfehler auf, die die
Live-App betreffen:
- Ein Turnier mit erfassten Startgebühren ließ sich **nicht löschen**.
  `TeamPayment` hatte keine Löschweitergabe, also versuchte SQLAlchemy den
  Primärschlüssel `team_payment.team_id` auf NULL zu setzen.
- Dasselbe bei `TournamentSettings`. Die Löschroute verdeckte es nur, weil
  sie die Einstellungen vorher von Hand wegräumt – jeder andere Aufrufer
  (Skript, Import) lief in den Fehler.

### 22:35 – Spielereignisse und Statistik (`f640245`)
Tore und Karten je Spiel, daraus Torschützenliste und Fair-Play-Wertung,
öffentlich und im Admin. Heikler Punkt war das Verhältnis zum Spielstand:
Der bleibt die führende Zahl (Plus-Knöpfe am Turniertag), wird beim Erfassen
eines Tores per Vorgabe mitgezogen, und wenn beide auseinanderlaufen, sagt
die App das offen statt eine Zahl stillschweigend zu überschreiben.
Eigentore zählen für den Gegner, aber nicht als Treffer des Schützen.

Export/Import nehmen jetzt Anmeldungen und Ereignisse mit.

### 22:58 – Siegerehrung (`8a17693`)
Platz 1–3 gab es nur als Podium in `main.js`. Jetzt rechnet der Server die
vollständige Endplatzierung für alle Finalformen – über Kategorien
(Platz steht fest / noch im Rennen / ausgeschieden / Gruppenphase), damit
die Liste auch mitten im Turnier sinnvoll ist. Dazu Ablaufliste für die
Siegerehrung (von hinten nach vorne) und druckbare Urkunden, A4 quer.

Erster Entwurf des Algorithmus war falsch: Ausgeschiedene landeten vor
Mannschaften, die noch im Rennen sind. Auf Kategorien umgebaut.

### 23:40 – Schiedsrichter (`f6ac2a3`)
Stammdaten, automatische Einteilung, Konfliktprüfung, Einsatzplan zum
Drucken. Die Zuteilung meidet die eigene Mannschaft und Zeitfenster, in
denen die eigene Mannschaft spielt, und verteilt die Last gleichmäßig.
Lässt sich eine Regel nicht einhalten, wird sie in zwei Stufen gelockert –
ein Betreuer der eigenen Mannschaft ist besser als kein Schiedsrichter,
und die Prüfung zeigt es an.

Mitgenommen: Die gedruckte Spielplan-Ansicht hatte **keine Anstoßzeiten**.
Jetzt zeigt sie Zeit und Schiedsrichter, aber nur wenn die Daten existieren.

Postgres-Migration gegen die laufende Dev-Datenbank mit Altdaten geprüft:
`referee_id` ergänzt, neue Tabellen angelegt, Bestand unverändert – auch
nach Container-Neustart.

### 23:50 – Refactoring
`admin.py` von 2882 auf 2018 Zeilen: `app/finalrunde.py` (413),
`app/backup.py` (465), `app/belege.py` (42) ausgezogen. Dafür
`app/blueprints.py`, damit mehrere Module Routen am `admin_bp` registrieren
können, ohne sich gegenseitig zu importieren.

Dabei in eine Falle getappt: `import app.admin` innerhalb von `create_app()`
überschreibt den lokalen Namen `app` (die Flask-App). Mit
`from app import admin as _admin_routes` gelöst, der Grund steht als
Kommentar daneben.

Inline-Skripte aus sechs Admin-Vorlagen in `static/js/admin/` ausgelagert
(~47 KB): dashboard, design, menu, export-import, organisation,
finals-setup. Die Werte aus der Vorlage (`SLUG`, `ALL_TEAMS`, …) bleiben als
kurzer Inline-Block davor. Eine Stelle brauchte Handarbeit: `maxRanks` stand
mitten in einer Funktion und wurde zu `MAX_RANKS` als Konstante.

Dazu `UX_REVIEW.md` und `ARCHITEKTUR.md`.
