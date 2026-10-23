# UX-Review CupPlan

Stand: Nacht vom 23. auf den 24.10.2026 · Grundlage: Codebasis v1.5 plus die
in dieser Nacht gebauten Erweiterungen, geprüft am Code und an der
Dev-Instanz (HTTP-Abrufe, gerenderte Seiten).

**Wie belastbar ist das?** Was hier steht, habe ich im Markup und im
Verhalten der Anwendung nachgemessen – Zahlen sind gezählt, nicht geschätzt.
Was ich *nicht* beurteilen kann: wie die Seiten tatsächlich aussehen. Ich habe
sie nicht in einem Browser gerendert und keine Screenshots gemacht. Alles,
was Optik, Lesbarkeit bei Sonnenlicht oder Bedienbarkeit mit nassen Händen
betrifft, muss du am Turniertag selbst beurteilen.

---

## Was gut ist

Das sollte man zuerst sagen, weil es die Grundlage für alles andere ist:

- **Die Zielgruppen sind verstanden.** Vier getrennte Ansichten für vier
  Situationen (Beamer im Zelt, Handy am Spielfeld, App-artige Mobilansicht,
  Desktop für die Turnierleitung) – das ist mehr Durchdachtheit, als die
  meisten Vereins-Apps haben.
- **Die Live-Ansicht kommt ohne Nachladen aus.** Socket.IO überträgt den
  Zustand, der lokale Timer läuft im Browser flüssig weiter und wird vom
  Server nur synchronisiert. Genau richtig: der Timer ruckelt nicht, wenn
  das WLAN im Sportheim schwach ist.
- **Druckansichten existieren überhaupt.** Spielplan, Kabinenschilder,
  Quittungen – das ist der Teil, den Software für Vereinsturniere
  üblicherweise vergisst, und den man am Turniertag am dringendsten braucht.
- **Gefährliche Aktionen sind abgesichert.** Gruppen mit Teams und Teams mit
  Spielen lassen sich nicht löschen; das Simulieren von Ergebnissen fragt
  nach dem Passwort. Beides ist vorausschauend.
- **Die Startgebühren-Verwaltung mit Quittungsdruck** inklusive Betrag in
  Worten ist ein Detail, das jemand mit Kassenerfahrung gebaut hat.

---

## Befunde, nach Dringlichkeit

### 1. Eingabefelder sind kaum beschriftet (hoch)

Gezählt: **154 Eingabefelder, davon 11** mit programmatischer Beschriftung
(`<label for="...">` oder `aria-label`). 44 haben nur einen Platzhalter,
99 haben gar keine Zuordnung – bei vielen steht ein `<label class="form-label">`
sichtbar daneben, aber ohne `for`/`id`-Verbindung.

Warum das zählt, auch ohne Screenreader:

- Ein Klick auf die Beschriftung setzt den Fokus nicht ins Feld. Auf dem
  Handy am Spielfeldrand ist das Trefferfläche, die man verschenkt.
- Platzhalter verschwinden beim Tippen. Wer im Anmeldeformular unterbrochen
  wird, weiß hinterher nicht mehr, was in das Feld gehört.
- Sprachsteuerung und Autofill des Browsers funktionieren schlechter.

**Zu tun:** `id` und `<label for>` paarweise setzen, Platzhalter nur noch als
Beispiel verwenden („z. B. SV Winkel II"), nicht als Beschriftung. Das ist
mechanische Arbeit, kein Umbau – gut verteilbar auf mehrere kleine Commits.
Die in dieser Nacht gebauten Seiten (Anmeldung, Ereignisse, Schiedsrichter,
Siegerehrung) habe ich schon so gebaut.

### 2. Rückmeldungen laufen über `alert()` und `confirm()` (hoch)

Gezählt: **über 60 Stellen** in den Admin-Templates. Vor allem
`dashboard.html` (15), `tournament_admin.html` (15) und
`match_control.html` (13).

Das Problem ist nicht der schlechte Stil, sondern das Verhalten am
Turniertag: ein modaler Browser-Dialog blockiert die Seite, auch die
Live-Aktualisierung. Wer auf dem Tablet „Spiel beenden" drückt und der
Dialog hängt hinter einem anderen Fenster, sieht einen scheinbar
eingefrorenen Spielplan. Dazu lassen sich `alert`-Dialoge nicht stapeln:
zwei schnelle Klicks, und die zweite Meldung geht verloren.

**Zu tun:** Eine kleine Hinweisleiste („Toast") in `admin_base.html`, die
Erfolg und Fehler drei Sekunden einblendet, und `confirm()` nur noch für
wirklich unumkehrbare Dinge (Löschen). Ein einziger Helfer, dann
schrittweise ersetzen. Ich habe darauf verzichtet, das heute Nacht
anzufangen: 60 Aufrufe umzubauen, ohne die Seiten im Browser sehen zu
können, wäre Pfusch gewesen. Die neuen Seiten nutzen stattdessen eine
Statuszeile im Seiteninhalt.

### 3. Vier Ansichten, viermal dasselbe Markup (mittel)

`index.html`, `phone.html`, `tv.html` und die Mobilansicht rendern denselben
Turnierzustand mit je eigenem Inline-JavaScript:
`phone.html` ~13 KB, `tv.html` ~11,5 KB, dazu `main.js` mit 547 Zeilen.

Das merkt man als Nutzer daran, dass Verbesserungen nur in einer Ansicht
ankommen. Beispiel aus dieser Nacht: das Podium für Platz 1–3 steckt
ausschließlich in `main.js` – die Handy- und TV-Ansicht hatten nie Zugriff
auf eine vollständige Endplatzierung. Deshalb habe ich sie serverseitig
nachgebaut; jetzt können alle Ansichten dieselbe Liste benutzen.

**Zu tun:** Die gemeinsame Darstellungslogik (Tabelle, Spielzeile, Timer,
Podium) in eine Datei unter `static/js/`, die alle vier Ansichten laden.
Kein Framework nötig.

### 4. Externe Abhängigkeiten aus dem Netz (mittel, turniertagkritisch)

Die Seiten laden aus dem Internet: Google Fonts (Inter), Tabler-CSS und -JS
von jsDelivr, Socket.IO von cdnjs, SortableJS von jsDelivr. Zusätzlich in
**drei verschiedenen Versionen** (SortableJS 1.15.2, 1.15.3 und 1.15.6) –
ein Zeichen dafür, dass die Versionen nirgends zentral stehen.

Am Turniertag ist das ein echtes Risiko: Die Beamer-Ansicht im Zelt hängt oft
an einem schwachen Mobilfunk-Hotspot. Fällt das Internet aus, während die
App selbst im lokalen Netz noch erreichbar wäre, sieht die TV-Ansicht
kaputt aus (keine Schrift, kein Layout) und die Drag-&-Drop-Sortierung im
Admin funktioniert nicht mehr.

**Zu tun:** Die vier Bibliotheken nach `static/vendor/` legen und von dort
ausliefern. Fonts lokal einbinden oder auf Systemschriften zurückfallen.
Danach läuft CupPlan ohne Internetzugang – nur das lokale Netz muss stehen.
Das ist der Punkt mit dem besten Verhältnis von Aufwand zu Nutzen auf dieser
Liste.

### 5. Der Spielplan war ohne Anstoßzeiten (behoben)

Vorher: Der Generator mischte die Paarungen zufällig und verteilte sie mit
`nummer % felder` auf die Plätze. Es gab keine Uhrzeiten, und dieselbe
Mannschaft konnte zeitgleich auf Feld 1 und Feld 2 angesetzt werden – in den
Seed-Testdaten hat die neue Prüfung genau das gefunden.

Behoben in dieser Nacht: echter Planer mit Zeitfenstern, Pausenregel je
Mannschaft, Mittagspause und einer Prüffunktion für bestehende Pläne. Die
gedruckte Spielplan-Ansicht zeigt jetzt Anstoßzeit und Schiedsrichter –
aber nur, wenn es die Daten auch gibt, sonst stünde dort eine leere Spalte.

### 6. Der Weg vom Anlegen zum Turniertag ist nicht geführt (mittel)

Ein neues Turnier braucht: Gruppen → Teams → Spielplan → Finalrundentyp →
Phase starten. Diese Reihenfolge steht nirgends. Die Turnieradministration
zeigt alle Bereiche gleichwertig nebeneinander; was als Nächstes dran ist,
muss man wissen.

**Zu tun:** Oben auf der Administrationsseite eine Zeile mit dem aktuellen
Stand und dem nächsten sinnvollen Schritt („4 Teams, keine Gruppen – zuerst
Gruppen anlegen"). Das ist wenig Code und nimmt genau die Unsicherheit,
die beim ersten Turnier entsteht.

### 7. Kleinere Beobachtungen

- **Zwei Wege zu derselben Einstellung.** Spielfelder und Finalrundentyp
  lassen sich in der Turnierliste, in der Administration *und* unter Design
  setzen. Wer sie an einer Stelle ändert, erwartet nicht, dass es noch zwei
  andere gibt. Eine Stelle sollte führen, die anderen darauf verweisen.
- **Umlaute in Systemmeldungen.** Der Bestandscode schreibt „Ungueltige
  Anmeldedaten", „geloescht", „Benoetigt". Nach außen sichtbarer Text sollte
  deutsche Umlaute benutzen; im Code-Kommentar ist die ASCII-Schreibweise
  in Ordnung. Ich habe die neuen Texte mit Umlauten geschrieben, den
  Bestand aber nicht angefasst – das sind viele kleine Änderungen in
  Dateien, die ich sonst nicht berührt hätte.
- **Die Versionsnummer steht an drei Stellen im Markup** (`admin_base.html`
  zweimal, dazu das Modal). Bei der nächsten Version wird eine davon
  vergessen. Gehört in eine Konstante.
- **Keine Leerzustände mit Handlungsaufforderung.** Eine leere Teamliste sagt
  nicht, wie man Teams anlegt. Die neuen Seiten machen es vor („Noch keine
  Anmeldungen. Teile den Link oben mit den Vereinen.").

---

## Was ich bewusst nicht gemacht habe

- **Die 60 `alert()`-Aufrufe ersetzt.** Ohne die Seiten im Browser zu sehen,
  hätte ich Rückmeldungen gebaut, die vielleicht gar nicht sichtbar sind.
- **Die Beschriftungen im Bestand nachgezogen.** 99 Felder in 15 Dateien
  anzufassen, ohne das Ergebnis ansehen zu können, ist ein schlechtes
  Verhältnis von Risiko zu Nutzen. Besser mit Playwright-Screenshots.
- **Die vier Ansichten zusammengelegt.** Das ist ein Umbau von einem halben
  Tag mit Browser, nicht von einer Nacht ohne.
