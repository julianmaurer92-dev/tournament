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
