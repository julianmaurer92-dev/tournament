# Design-Logbuch – CupPlan, neues UI

| | |
|---|---|
| **Start** | Samstag, 24.10.2026, **20:05 Uhr** |
| **Ende** | 25.10.2026, **01:05 Uhr** (Start + 5 h) |
| **Abschluss ab** | **00:35 Uhr** |
| **Branch** | `ui/neues-design` |
| **Dev-Instanz** | http://192.168.8.172:8092 (Compose-Projekt `cupplan-design`) |

---

## Vorbemerkungen

### Basis-Branch: `ux/keynote-redesign`

Der Auftrag lässt die Wahl zwischen Haupt-Branch, `nightly/2026-10-24` und
`ux/keynote-redesign`. Ich nehme den letzten – aus drei Gründen:

1. **Er ist der neueste Stand** (676d134, heute 17:14) und enthält 508
   grüne Tests. `main` steht noch auf dem Initial-Commit von vor neun
   Monaten.
2. **Er bringt Infrastruktur mit, die ich sowieso bräuchte:** ein
   Token-System mit Farbrollen, einen Kontrastprüfer, `app/farben.py`
   (Palette aus einer Akzentfarbe ableiten), `app/themes.py` mit der
   Abbildung alter Theme-Namen, ein Navigationsmodul, ein Icon-Sprite.
   Diese Teile noch einmal zu bauen wäre in fünf Stunden verschwendete
   Zeit.
3. **Das Gestalterische darüber ist trotzdem frei.** Tokens sind
   Variablennamen, keine Gestaltung. Welche Werte darin stehen, wie die
   Seiten aufgebaut sind, wie Navigation und Komponenten aussehen –
   das entscheide ich hier neu.

Was ich bewusst **nicht** übernehme: die Seitenleiste, die Kartenraster,
die Farbwelt, die Typografie, die Komponentensprache. Das neue Design
beginnt bei null.

### Produktion

Wie schon zweimal zuvor geprüft: **CupPlan läuft nicht auf dieser VM.**
`docker compose ps` in `/home/mj/cupplan` liefert eine leere Tabelle;
`docker ps` zeigt nur GLPI, smart-pantry, staedtetrip-umfrage, Dockge und
meine eigenen Entwicklungsinstanzen. cupplan.de zeigt auf einen externen
VPS (85.215.206.46).

Die Vorsichtsregeln gelten trotzdem: eigener Klon
(`/home/mj/cupplan-design`), eigenes Compose-Projekt, eigener Port 8092,
eigene Volumes, kein Deployment.

### Drei genannte Seiten gibt es im Repository nicht

`/admin/sponsors`, `/admin/smtp-settings` und `/t/<slug>/mobile/` haben
keine Route im Code. Siehe `docs/design/FUNKTIONEN.md` – ich baue sie
nicht neu, das wären neue Fachfunktionen. Die gewünschte **App-artige
Handy-Ansicht mit Leiste unten** setze ich dagegen um: Das ist reine
Gestaltung und betrifft die vorhandene Route `/t/<slug>/phone/`.

---

## Verlauf

### 20:05 – Aufbau

Klon, Branch, eigener Stack auf Port 8092, Testdaten eingespielt:
drei Turniere (eines beendet mit Finalrunde, eines laufend, eines mit
geöffneter Anmeldung), Wappen, Spielerlisten, Speisekarte,
Benutzer aller drei Rollen. Dazu ein **laufendes Spiel** mit Uhr bei
3:57, Spielstand 2:1, drei Torschützen und einer gelben Karte – damit
die Live-Ansichten beim Screenshotten etwas zu zeigen haben.

Funktionsinventar aus `app.url_map` erhoben: 113 Routen, 44 Seiten,
64 Aktionen. Steht in `docs/design/FUNKTIONEN.md` und ist die Prüfliste
für den Schluss.

### 20:25 – Design-Konzept: drei Proben, eine Entscheidung

Drei Richtungen gebaut und nebeneinander angesehen (die Proben stehen
unter `/design-lab/` und bleiben als Beleg stehen):

| Richtung | Idee | Urteil |
|---|---|---|
| **Tafel** | Anzeigetafel als Bauprinzip – kräftiger Rand, Beschriftungsstreifen, Tabellenziffern | Bauprinzip übernommen |
| **Kreide** | Spielfeldlinien, hell auf Grün | **abgelehnt** |
| **Kiosk** | warmes Papierweiß, dicke Kacheln, große Ziele | Ergonomie übernommen |

**Warum „Kreide" als Ganzes durchgefallen ist:** Ein grüner
Hintergrund überall macht die Vereinsfarbe wertlos – sie hat nichts
mehr, wogegen sie sich absetzen könnte – und zwingt jeden Text auf
einen Kontrast-Drahtseilakt. Geblieben sind die Linien als Signatur.

**Die eigentliche Erkenntnis aus den Proben:** CupPlan hat nicht zwei
Geschmäcker, sondern **zwei Betriebsarten**. Hell heißt bedienen
(draußen, Sonne, eine Hand), dunkel heißt zeigen (Zelt, Beamer). Das
ist keine Entweder-oder-Frage, sondern genau das, wofür ein
Token-System da ist.

Name der Sprache: **Anpfiff**. Präfix `ap-`.

### 20:29 – Fundament (`fad7bae`)

Tokens, 17 geprüfte Theme-Varianten, drei Schriften. Der erste
Kontrastlauf fand **35 Verstöße** – und zwar denselben Denkfehler an
einer einzigen Variablen: `--ap-kante` trug gleichzeitig den Zierrand
einer Tafel und den Rand eines Eingabefelds. WCAG 1.4.11 verlangt 3:1
für Bedienelemente, nicht für Zierde. Zwei Rollen daraus gemacht,
Problem weg.

### 21:13 – Bausteine und Styleguide (`d97aabe`)

Tafel, Knopf, Segment, Tabelle, Schublade, Meldung – und
`/admin/styleguide`, wo alles in jedem Theme zu sehen ist.

### 21:13 – Spielsteuerung (`3845bfe`)

Siehe Notion. Gemessen: Inhaltshöhe exakt 844 px auf einem 844-px-
Bildschirm, mit zwei Spielfeldern gleichzeitig.

### 21:26 – Öffentliche Ansichten (`aec0615`)

Live-Spiel als Bühne, Reiter von oben nach unten.

### 21:39 – Beamer (`822adc3`)

Anpfiff auf dem Beamer, „Anzeigetafel" als Vorgabe.

### 22:33 – Alle Adminseiten (`94aaabb`)

`admin_base.html` ist eine dünne Schicht über der Anpfiff-Hülle
geworden, `_bausteine.html` eine Brücke auf die neuen Makros. Damit
bekamen rund zwanzig Seiten auf einen Schlag die neue Hülle.

Das war die Stelle mit den meisten Überraschungen – fünf Fehler, alle
erst im Browser sichtbar, alle in der Commit-Nachricht beschrieben.
Der lehrreichste: Eine zu grobe Regel von mir
(`[class*="-grid"]` auf eine Spalte zwingen) machte auch Raster platt,
die auf dem Handy richtig waren. Zurückgenommen und präzisiert.

### 22:45 – Theme-Galerie

Neun Karten mit einer Miniatur der echten Oberfläche. Ein Klick wendet
an, Rückgängig über die Meldung. „Anzeigetafel" sperrt die helle
Variante, weil es keine gibt.

---

### 23:40 – Abschluss

Tests: **512 bestanden, 0 offen.** Zwei Dateien mussten mitziehen:

- `tests/test_themes.py` – die 32 alten Tests prüften den vorherigen
  Theme-Katalog und sind zu Recht durchgefallen. 36 neue, die vor
  allem das prüfen, worauf es ankommt: dass niemandem seine
  Einstellung wegbricht.
- **Ein echter Rückschritt, den die Tests gefangen haben:** Das
  Sicherheits-Warnbanner („SECRET_KEY ist ein Vorgabewert") war in
  meiner neuen Hülle verschwunden. Das ist der einzige Ort, an dem
  ein Superadmin davon erfährt. Wiederhergestellt – jetzt als Tafel
  in der Warnfarbe.

52 Nachher-Bilder in `docs/design/nachher/`, dazu 17 Theme-Bilder in
`docs/design/themes/`.

---

## Was fertig wurde

| Bereich | Zustand |
|---|---|
| Gestaltungssprache „Anpfiff" mit drei gebauten Proben | fertig |
| Design-Tokens, 9 Themes (17 Varianten), WCAG-AA-Prüfer | fertig |
| Drei Schriften, selbst gehostet, 502 KB | fertig |
| Bausteine + Styleguide unter `/admin/styleguide` | fertig |
| App-Hülle: Seitenleiste + **Leiste unten** auf dem Handy | fertig |
| Spielsteuerung komplett neu | fertig |
| Live-, Handy- und Beamer-Ansicht | fertig |
| Beamer: Präsentationsmodus, Theme „Anzeigetafel" | fertig |
| Theme-Galerie mit echten Miniaturen | fertig |
| Alle rund zwanzig Adminseiten in der neuen Hülle | fertig |
| Befehlspalette `Strg/Cmd + K` | übernommen, auf Anpfiff umgestellt |
| Druckansichten (Spielplan, Quittungen, Kabinenschilder) | **nur über die Brücke** – Farben und Schrift stimmen, das Layout ist unverändert |
| Adminseiten mit eigenem Anpfiff-Markup | **nur Spielsteuerung, Design und Styleguide** – der Rest läuft über die Tabler-Brücke |

## Was offen blieb

In dieser Reihenfolge würde ich weitermachen:

1. **Übersicht und Spielplan in echtem Anpfiff-Markup.** Sie sehen
   heute richtig aus, benutzen aber noch Tabler-Karten und das alte
   Seitenlayout. Hier liegt der größte verbliebene Gewinn – vor allem
   die Bearbeitung direkt am Element statt im Formular.
2. **Druckansichten.** Sie erben Farben und Schrift, aber das Layout
   stammt unverändert aus dem alten Stand.
3. **Assistent für „Neues Turnier".** Heute elf Klicks über drei
   Formulare.
4. **axe-core-Durchlauf.** Kontrast ist nachgerechnet, Tastatur und
   Fokus sind von Hand geprüft – eine automatische Prüfung lief nicht.
5. **Die beiden Brücken abbauen.** `anpfiff-tabler.css` und der
   Aliasblock in `anpfiff.css` sind ausdrücklich Übergang. Jede Seite,
   die auf `.ap-tafel` und `.ap-knopf` umgestellt wird, macht ein
   Stück davon überflüssig.
6. **PWA-Manifest und App-Symbol** im neuen Stil.

## Deployment auf dieser VM

> **Nichts davon wurde ausgeführt.** Der Auftrag schließt Deployment
> aus. Die Schritte stehen hier, damit sie jemand bewusst gehen kann.

Zur Lage: CupPlan läuft **nicht** auf dieser VM. `docker compose ps`
in `/home/mj/cupplan` liefert eine leere Tabelle; cupplan.de zeigt auf
einen externen VPS (85.215.206.46). Die Schritte gelten für den
Rechner, auf dem die Produktion tatsächlich läuft.

### 1. Sichern – zuerst, immer

```bash
cd /pfad/zur/produktion
mkdir -p ~/cupplan-backups/$(date +%F)
docker compose exec -T db pg_dump -U cupplan cupplan \
    > ~/cupplan-backups/$(date +%F)/vor-anpfiff.sql
ls -lh ~/cupplan-backups/$(date +%F)/
git rev-parse HEAD > ~/cupplan-backups/$(date +%F)/commit-vorher.txt
```

Die Datei muss größer als null sein. Ist sie es nicht, hier aufhören.
Zusätzlich über die Oberfläche: **Sicherung → Export** als JSON.

### 2. Branch holen und bauen

```bash
git fetch origin ui/neues-design
git switch ui/neues-design
docker compose build web
docker compose up -d web
docker compose logs -f web      # bis "Running on" erscheint
```

**Keine Datenbank-Migration.** Am Datenmodell hat sich nichts
geändert. Die einzige Änderung an gespeicherten Daten: Der Wert der
Einstellung `theme` wird beim nächsten Speichern auf die neue
Schreibweise normalisiert (`rasen:hell`). Alte Werte werden beim Lesen
weiterhin verstanden – beide Generationen, siehe
`app/themes.py` → `ALTE_NAMEN`.

**Wichtig:** `CUPPLAN_DESIGN_LAB` darf in der Produktion **nicht**
gesetzt sein. Ohne die Variable existiert `/design-lab/` gar nicht.

### 3. Nachsehen, ob es wirklich läuft

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://cupplan.de/
curl -sS -o /dev/null -w '%{http_code}\n' https://cupplan.de/admin/login
```

Im Browser, in dieser Reihenfolge:

1. **Anmelden** – Seitenleiste links, Turnier oben im Umschalter.
2. **`/admin/styleguide`** – sieht alles richtig aus? Hell und dunkel
   umschalten.
3. **Spielsteuerung eines laufenden Spiels, am Handy** – passt alles
   ohne Scrollen? Öffnet das große **Tor** die Schützenliste?
4. **Ein Tor eintragen und sofort zurücknehmen.**
5. **Design → ein Theme anklicken** – wechselt die Oberfläche sofort?
   Zeigt die Live-Ansicht in einem zweiten Tab nach dem Neuladen
   dasselbe?
6. **Beamer-Ansicht, „Präsentieren"** – blättert sie von allein?
7. **Sicherung → Export** – lädt die JSON-Datei und enthält
   Mannschaften und Spiele?

### 4. Zurück, falls etwas nicht stimmt

```bash
git switch $(cat ~/cupplan-backups/$(date +%F)/commit-vorher.txt)
docker compose build web && docker compose up -d web
```

Die Datenbank muss **nicht** zurückgespielt werden – es gab keine
Schemaänderung.

### 5. Guter Zeitpunkt

Nicht am Turniertag. Nicht am Abend davor. In einer ruhigen Woche,
damit ein paar Tage Zeit bleiben, bevor es darauf ankommt.
