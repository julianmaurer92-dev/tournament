# Architektur CupPlan – Bestand und Empfehlung

Stand: Nacht vom 23. auf den 24.10.2026, nach der Nachtschicht auf
`nightly/2026-10-24`.

---

## 1. Wie es aufgebaut ist

```
run.py                     create_app() + socketio
app/__init__.py            App-Factory: Konfiguration, DB, Login, SocketIO,
                           Google-OAuth, _migrate_db(), _ensure_admin(),
                           Blueprint-Registrierung
app/blueprints.py          admin_bp – damit mehrere Module Routen daran
                           haengen koennen, ohne sich zu importieren
app/auth.py                superadmin_required, editor_required,
                           tournament_required
app/security.py            Konfigurationswarnungen, Anmeldebremse,
                           Formularbremse
app/models.py              Datenmodell + Tabellenberechnung
app/routes.py              oeffentliche Ansichten + /api/state
app/socket_events.py       Socket.IO: join_tournament, state_update

app/admin.py               Adminbereich: Auth, Turniere, Dashboard,
                           Gruppen, Teams, Spiele, Timer, Phasen,
                           Speisekarte, Benutzer, Organisation
app/finalrunde.py          Finalbaeume erzeugen, Paarungen vorausberechnen,
                           Sieger weiterleiten
app/backup.py              JSON-Export/-Import
app/belege.py              Betraege in Worten (Quittungen)

app/anmeldung.py           Vereinsanmeldung (oeffentlich + Admin)
app/ereignisse.py          Tore und Karten erfassen, Statistik ausliefern
app/statistik.py           Torschuetzen, Fair-Play (reine Logik)
app/spielplan.py           Spielplanung: Slots, Felder, Zeiten (reine Logik)
app/platzierung.py         Endplatzierung (reine Logik)
app/siegerehrung.py        Siegerehrung, Urkunden
app/schiedsrichter.py      Zuteilungslogik (reine Logik)
app/schiedsrichter_routes.py  Schiedsrichter-Routen

app/templates/             Jinja, Tabler-CSS
app/static/js/admin/*.js   ausgelagerte Admin-Skripte
tests/                     400+ Tests, davon ~120 ohne Datenbank
scripts/seed_dev.py        Testwochenende auf Knopfdruck
```

Technisch: Flask 3 + Flask-SQLAlchemy auf Postgres 16, ein gunicorn-Worker
mit gevent-WebSocket, Socket.IO für die Live-Aktualisierung.

---

## 2. Was gut trägt – und warum man es nicht anfassen sollte

**Das Datenmodell.** Für eine „vibe-gecodete" App ist es überraschend
tragfähig: Turnier als Wurzel, Einstellungen als Key-Value je Turnier,
saubere Trennung der Mandanten über `tournament_id`, ein Rollenmodell mit
Turnier-Zugang. Ich habe in dieser Nacht fünf Tabellen ergänzt
(`registration`, `match_event`, `referee` plus Spalten) und musste dafür
nichts umbauen – das ist das beste Zeugnis, das ein Datenmodell bekommen kann.

**Die Einstellungen als Key-Value.** Klingt nach einer Notlösung, ist hier
aber richtig: Turniere unterscheiden sich in Dutzenden Kleinigkeiten
(Spielzeit, Farben, was öffentlich sichtbar ist), und jede davon als Spalte
hätte zwanzig Migrationen gekostet. Die zehn Schlüssel, die ich ergänzt
habe (`registration_*`, `urkunde_*`), brauchten **keine** Migration, weil
`get_setting()` auf die Standardwerte zurückfällt.

**Ein Worker mit gevent.** Für ein Vereinsturnier mit ein paar hundert
Zuschauern ist das genau die richtige Größe. Mehr Worker wären hier kein
Fortschritt, sondern ein Problem (siehe 3.3).

**Die Mandantentrennung ist konsequent.** Ich habe das systematisch geprüft:
Jede Route, die eine ID aus der URL nimmt, vergleicht sie gegen
`g.tournament.id`. Die typische Lücke – ein Spiel aus Turnier A über die
URL von Turnier B manipulieren – existiert nicht. 30 Tests halten das jetzt
fest.

---

## 3. Empfehlungen, nach Verhältnis von Nutzen zu Aufwand

### 3.1 Bibliotheken lokal ausliefern (klein, wirkt am Turniertag)

Die App lädt Tabler-CSS/-JS, Socket.IO, SortableJS und Google Fonts aus dem
Internet – SortableJS sogar in drei Versionen (1.15.2, 1.15.3, 1.15.6).
Fällt am Turniertag das Internet aus, während das lokale Netz noch steht,
sieht die Beamer-Ansicht kaputt aus und Drag & Drop im Admin funktioniert
nicht mehr.

**Empfehlung:** Die vier Dateien nach `app/static/vendor/` legen, von dort
ausliefern, eine Version festlegen. Ein Nachmittag Arbeit, danach läuft
CupPlan ohne Internetzugang.

### 3.2 Schema-Änderungen mit Alembic statt SQL-Liste (mittel, wichtig)

`_migrate_db()` ist eine Liste von `ALTER TABLE ... IF NOT EXISTS`, die bei
jedem Start läuft. Das funktioniert, solange alle Änderungen additiv sind –
ich habe mich daran gehalten und `match.referee_id` genauso ergänzt. Die
Grenzen sind aber konkret:

- Keine Historie: man kann nicht sehen, welcher Stand welche Spalten hat.
- Kein Zurück: ein Fehler lässt sich nicht rückwärts abspielen.
- `ALTER COLUMN ... TYPE TEXT` läuft bei jedem Start erneut; bei einer
  großen Tabelle sperrt das den Start.
- Nichts hindert jemanden daran, ein `DROP COLUMN` in die Liste zu schreiben.
  Dann sind die Daten weg, beim nächsten Neustart, ohne Rückfrage.

**Empfehlung:** Alembic einziehen. Der Bestand wird als „Initial-Revision"
gestempelt, danach bekommt jede Änderung eine Datei mit `upgrade()` und
`downgrade()`. Aufwand: ein halber Tag. Der Gewinn ist, dass man eine
Migration vorher an einer Kopie durchspielen kann.

### 3.3 Zustand im Prozessspeicher – der Grund, warum es ein Worker bleiben muss

Drei Dinge liegen im Speicher des Prozesses, nicht in der Datenbank:

1. die Anmeldebremse (`app/security.py`)
2. die Formularbremse für das Anmeldeformular
3. der Socket.IO-Nachrichtenverteiler

Mit einem gunicorn-Worker ist das korrekt und sparsam. Mit zwei Workern
wäre alles drei kaputt: Die Bremse ließe sich durch Glück umgehen, und ein
`state_update` erreichte nur die Zuschauer, die zufällig am selben Worker
hängen – die Hälfte des Publikums sähe den Spielstand nicht.

**Empfehlung:** Es beim einen Worker lassen und das in `docker-compose.yml`
als Kommentar festhalten (ist dort noch nicht dokumentiert, nur die
Begründung für gevent). Wird mehr Last nötig, braucht es **vorher** Redis
als Nachrichtenverteiler (`socketio.init_app(message_queue=...)`) und für
die Bremsen. Nicht andersherum.

### 3.4 CSRF-Token nachrüsten (mittel, Sicherheit)

Die Formulare haben keine CSRF-Token. Ich habe das in dieser Nacht
abgemildert, indem das Sitzungs-Cookie `SameSite=Lax` bekommen hat – damit
senden Browser es bei POST-Anfragen fremder Seiten nicht mit, und der
Angriff ist praktisch abgedeckt.

„Praktisch" ist aber nicht „vollständig": Ein `GET`, der etwas verändert,
wäre weiter angreifbar, und bei älteren Browsern greift `Lax` nicht.

**Empfehlung:** Flask-WTF mit `CSRFProtect`, dann Schritt für Schritt
`{{ csrf_token() }}` in die Formulare und den Header `X-CSRFToken` in die
`fetch()`-Aufrufe. Das betrifft rund 40 Routen und jeden `fetch()` im
Frontend – deshalb habe ich es nachts nicht angefangen: halb eingebauter
CSRF-Schutz bedeutet, dass Formulare still nicht mehr funktionieren.
Mit Playwright-Tests im Rücken ist es ein ruhiger Nachmittag.

### 3.5 `admin.py` weiter aufteilen (mittel)

Vor dieser Nacht: 2582 Zeilen, alles in einer Datei. Jetzt: 2018 Zeilen,
nachdem Finalrunde (413), Backup (465) und Belege (42) ausgezogen sind.
Das ist besser, aber noch nicht gut. Sinnvolle nächste Schnitte, in dieser
Reihenfolge:

1. **Spiele und Timer** (`create_match`, Score, Status, Timer,
   `match_control`, CSV-Import) – der am Turniertag heikelste Teil,
   gehört einzeln lesbar.
2. **Turnierphasen** (`/api/phase/*`) – sieben Routen, die zusammen eine
   Zustandsmaschine bilden, die nirgends als solche benannt ist.
3. **Organisation** (Zahlungen, Quittungen, Kabinenschilder, Druckplan).
4. **Benutzer** und **Speisekarte** – jeweils klein und unabhängig.

Das Muster steht bereit: Blueprint aus `app/blueprints.py` holen, Modul in
`create_app()` importieren. Genau so hängen `backup.py` und die
Nacht-Module schon dran.

### 3.6 Die Phasenlogik als eigene Schicht (mittel, verhindert Fehlbedienung)

Ein Turnier hat Phasen: `GROUP_STAGE` → `FINALS` → `FINISHED`, dazu
Rücksprünge. Diese Zustandsmaschine steckt verteilt in sieben Routen und
einem Einstellungsschlüssel (`tournament_phase`). Welche Übergänge erlaubt
sind, steht nirgends zusammen – jede Route prüft es für sich.

Folge: Es gibt Wege in Zustände, die inhaltlich unsinnig sind, etwa eine
Finalrunde starten, solange Gruppenspiele offen sind.

**Empfehlung:** Ein Modul `app/phasen.py` mit den erlaubten Übergängen und
ihren Bedingungen, und einer Funktion `pruefe_uebergang(turnier, ziel)`,
die eine verständliche Begründung zurückgibt. Die Routen rufen nur noch
diese Funktion. Gut testbar, weil reine Logik – wie `spielplan.py`,
`platzierung.py` und `schiedsrichter.py`, die in dieser Nacht nach diesem
Muster entstanden sind und zusammen in unter vier Sekunden durchlaufen.

### 3.7 Die Darstellungslogik der vier Ansichten zusammenlegen (größer)

`index.html`, `phone.html`, `tv.html` und die Mobilansicht rendern denselben
Zustand mit je eigenem Inline-JavaScript. Verbesserungen kommen dadurch nur
in einer Ansicht an (Beispiel: das Podium gab es nur in `main.js`).

**Empfehlung:** Die gemeinsamen Bausteine – Tabelle, Spielzeile, Timer,
Podium, Platzierung – in ein Modul unter `static/js/`, das alle vier laden.
Kein Framework nötig und kein Big Bang: Baustein für Baustein, jeweils mit
einem Playwright-Test, der vorher und nachher dasselbe Bild zeigt.

### 3.8 Die Testsuite wird langsam (klein, aber bald fällig)

400 Tests brauchen rund 11 Minuten. Die reine Logik ist schnell
(`spielplan`, `statistik`, `platzierung`, `schiedsrichter`: ~120 Tests in
unter 4 Sekunden), die Last liegt bei den Routen-Tests: pro Test
`drop_all/create_all` plus Fixtures.

**Empfehlung:** `pytest-xdist` (`-n 4`) bringt sofort Faktor 3; dazu
Transaktions-Rollback statt `drop_all/create_all` pro Test. Und beim
Weiterbauen weiter dem Muster folgen: Entscheidungen in reine Funktionen,
Routen nur noch dünn drumherum. Das ist der Grund, warum die Logikmodule
dieser Nacht so schnell sind.

---

## 4. Was ich bewusst nicht gemacht habe

| Nicht gemacht | Warum |
|---|---|
| CSRF-Token eingebaut | 40 Routen und jeder `fetch()`; halb eingebaut heißt stille Fehler |
| Alembic eingezogen | braucht einen Lauf gegen eine Kopie der echten Datenbank – die ich nicht habe |
| Start bei unsicherem `SECRET_KEY` abgebrochen | die App läuft live; ein verweigerter Start wäre schlimmer als die Warnung. Stattdessen Log + Banner für Superadmins |
| Fremdschlüssel-Constraint für `match.referee_id` | `ALTER` mit Constraint auf eine Tabelle mit Altdaten ist riskanter als der Nutzen; die ORM pflegt die Zuordnung |
| Die vier Ansichten zusammengelegt | Umbau mit Browser, nicht ohne |
| Bestehende `alert()`-Aufrufe ersetzt | siehe UX_REVIEW.md |

---

## 5. Reihenfolge, wenn ich einen Tag hätte

1. Bibliotheken lokal ausliefern (3.1) – wirkt sofort am Turniertag
2. Alembic (3.2) – bevor die nächste Schema-Änderung kommt
3. CSRF (3.4)
4. `app/phasen.py` (3.6) – verhindert Fehlbedienung unter Zeitdruck
5. `admin.py` weiter aufteilen (3.5), Schnitt für Schnitt
6. Ansichten zusammenlegen (3.7)
