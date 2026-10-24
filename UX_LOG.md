# UX-Logbuch – CupPlan

**Start:** Samstag, 24.10.2026, 09:18 Uhr
**Geplantes Ende:** 17:18 Uhr · **Abschluss ab:** 16:48 Uhr
**Branch:** `ux/keynote-redesign` · **Arbeitsordner:** `/home/mj/cupplan-ux`
**Dev-Instanz:** http://localhost:8091 (Compose-Projekt `cupplan-ux`)

---

## Befunde zum Auftrag

### Die Produktion läuft nicht auf dieser VM

Der Auftrag sagt, die Live-App laufe als Docker-Container aus
`/home/mj/cupplan` auf dieser Maschine. `docker ps` zeigt: die einzigen
CupPlan-Container sind meine eigenen Dev-Container. Die Produktion liegt auf
einem externen VPS. Für diesen Auftrag ist das ohne Folgen – ich arbeite
ohnehin nur im Klon `/home/mj/cupplan-ux` und teste gegen Port 8091.
Den alten Dev-Stack (`cupplan-dev`, Port 8090) habe ich heruntergefahren,
damit die vier Kerne dieser Maschine nicht von zwei Instanzen geteilt werden.

### Drei der genannten Seiten gibt es im Repository nicht

Maßgeblich ist laut Auftrag ausschließlich der Code im Repository. Dort
fehlen drei Seiten aus der Liste – sie liefern 404:

| Seite | Status im Repo |
|---|---|
| `/t/<slug>/mobile/` | existiert nicht |
| `/admin/sponsors` | existiert nicht |
| `/admin/smtp-settings` | existiert nicht |

Sie existieren nur auf dem VPS. Ich überarbeite sie deshalb nicht und baue
sie auch nicht nach – das wäre eine neue Fachfunktion und damit außerhalb
des Auftrags.

### Basis-Branch

Basis ist `nightly/2026-10-24`, nicht `main`. Grund: `main` steht auf dem
Initial-Commit, `nightly` ist 13 Commits weiter und enthält den tatsächlich
genutzten Funktionsstand. Auf `main` aufzusetzen hieße, gegen eine App zu
entwerfen, die es so nicht gibt.

---

## Verlauf

### 09:18 – Aufbau
Klon, eigener Compose-Stack (`cupplan-ux`, Port 8091, eigene Volumes),
Testdaten. Das Seed-Skript erweitert: Vereinswappen (selbst erzeugte SVGs),
Spielerlisten je Team (für die Torschützen-Schnellauswahl), ein beendetes
Turnier mit Halbfinale, Finale und Spiel um Platz 3, und eine geöffnete
Vereinsanmeldung mit Beispielen. Ohne diese Zustände sieht man beim
Screenshotten die halbe Oberfläche nie.

Vorher-Screenshots: 26 Seiten je 1440 px und 390 px → `docs/ux/vorher/`.

### 09:35 – Design-Tokens und Themes (`tokens.css`)
Farben, Abstände, Radien, Schatten, Schrift und Bewegung an einer Stelle.
Entscheidender Unterschied zu vorher: **Farbrollen statt Farbnamen**.
`--flaeche-erhoben` sagt, wozu der Wert da ist; ein neues Theme setzt
~16 Werte und wirkt sofort überall.

10 Themes (Rasen, Mitternacht, Schiefer, Ozean, Ziegel, Forst, Bernstein,
Veilchen, Papier, Stadion), jedes hell **und** dunkel – 20 Varianten.

`scripts/kontrast_pruefen.py` rechnet alle Kombinationen gegen WCAG AA nach.
Der erste Lauf fand **20 echte Verstöße**: meine Rahmenfarbe erreichte
nirgends die geforderten 3:1 für Bedienelemente. Statt alle Trennlinien
dunkler zu machen, habe ich die Rolle getrennt – dekorative Linien
(`--rand`) dürfen leise sein, Rahmen von Eingabefeldern (`--rand-interaktiv`)
nicht. Dazu den Rasen-Akzent von `#0f8a4a` auf `#0d7c42` korrigiert
(weiße Schrift darauf: 4,42:1 → 5,28:1). Jetzt bestehen alle 20 Varianten.

### 09:40 – Bausteine (`bausteine.css`) und Icons
Knöpfe, Karten, Tabellen, Abzeichen, Eingabefelder, Sheets, Toasts, leere
Zustände – alles nur über Tokens. Berührziele mindestens 44 px.

Icons: 53 Symbole aus Tabler Icons (MIT) als eigener Sprite, 11 KB. Vorher
waren es 339 Emoji und HTML-Entities quer durch die Vorlagen – in jedem
Betriebssystem anders aussehend und nicht einfärbbar.

### 09:45 – Vereinsfarbe (`app/farben.py`)
Aus einer Primärfarbe wird eine Palette: Hover-Ton, leise Fläche, Fokusring
und – das Wichtige – **die Schriftfarbe darauf**. Eine knallgelbe
Vereinsfarbe mit weißer Schrift ist unlesbar; das entscheidet jetzt der
Kontrast, nicht das Gefühl.

Ein Test über 216 Farben fand dabei einen Fehler in meiner eigenen Funktion:
Ich verglich gegen reines Schwarz, lieferte aber `#111111` aus – bei
Mitteltönen wie `#996699` fiel dadurch die schlechtere Wahl (4,24:1 statt
4,45:1). Behoben.

---

## Verlauf (Fortsetzung)

### 10:40 – Spielsteuerung und Navigation (`d7f085e`)

Siehe Notion. Kurz: Tor mit Torschütze von neun Schritten auf zwei, alles
ohne Scrollen auf 390 × 844, keine Bestätigungsdialoge mehr (stattdessen
Rückgängig), eine Seitenleiste statt pro Seite eigener Menüs.

### 11:55 – Theme-Galerie (`f63a427`)

Große Vorschaukarten, ein Klick wendet an. Dabei fiel ein echter Fehler
auf, siehe unten.

### 12:40 – „Mein Team" in der Handy-Ansicht (`41fd0da`)

Einmal die Mannschaft wählen, danach steht das nächste Spiel oben.
4 Klicks → 0.

### 13:16 – Befehlspalette (`44ac76d`)

`Strg/Cmd + K` sucht über Seiten, Aktionen, Mannschaften, Spiele und
Themes; `?` zeigt die Tastenkürzel.

**Anmerkung zur Ordnung:** In denselben Commit ist versehentlich das
Aufräumen der alten Kopfzeilen-Menüs geraten (15 Vorlagen trugen neben
der neuen Seitenleiste noch ihre alte Navigation). Inhaltlich gehört das
zur Navigation, nicht zur Suche. Ich korrigiere es nicht nachträglich,
weil der Commit bereits gepusht ist und der Auftrag kein Umschreiben der
Historie erlaubt.

### 14:00 – Beamer-Präsentation

Die Beamer-Ansicht zeigte bisher immer alle drei Spalten gleichzeitig
und hatte fest eingebaute Farben – immer dunkelblau, unabhängig vom
gewählten Theme. Jetzt: Design-Tokens (alle 20 Varianten wirken, auch
„Papier" für ein helles Zelt und „Stadion" für maximale Entfernung) und
ein Präsentationsmodus, der immer nur eine Sache zeigt und von selbst
weiterblättert.

---

## Gefundene Bugs

*(fachliche Fehler, die mir auffallen – nicht Teil dieses Auftrags)*

1. **Die Einstellungs-Route kannte nur sechs der zehn Theme-Namen.**
   `navy`, `forest`, `amber` und `violet` standen in der Auswahl, wurden
   beim Speichern aber stillschweigend verworfen – man klickte, und es
   passierte nichts. Ursache: Die Namensliste stand doppelt im Code.
   *Behoben*, weil sie die Theme-Galerie blockiert hätte: Jetzt
   entscheidet `app/themes.py` allein.

2. **Die Beamer-Ansicht ignorierte die Theme-Einstellung.**
   `data-theme="{{ site_settings.theme or 'dark' }}"` stand zwar im
   HTML, aber darunter überschrieben feste Farbwerte alles. Wer das
   Theme umstellte, sah auf dem Beamer keinen Unterschied. *Behoben*,
   weil es den Auftragspunkt „Theme gilt auch auf dem Beamer" direkt
   betraf.

*Geprüft und in Ordnung:* Ich hatte einen dritten Punkt notiert – in
`tv.html` könnten Mannschaftsnamen ungefiltert in `innerHTML` landen.
Das Nachzählen aller 30 Einsetzungen in den Template-Literalen zeigt:
Jeder Name läuft durch `esc()`, auch `final_label` und `group_name`.
Der Punkt war falsch und ist deshalb gestrichen.

---

## Ideen für später

- **Live-Seite überspringen, wenn nichts läuft.** Die Präsentation zeigt
  die Live-Seite auch dann 20 Sekunden lang, wenn gerade kein Spiel
  angepfiffen ist. Sie sagt inzwischen, was als Nächstes kommt – ein
  automatisches Überspringen wäre trotzdem besser.
- **Dauer je Seite einstellbar.** 20/15/15 Sekunden sind geraten. Wer
  acht Gruppen hat, braucht auf der Tabellenseite länger.
- **Zweiter Bildschirm.** Vereine mit zwei Beamern würden gern links die
  Tabellen und rechts die Spiele stehen lassen, statt zu blättern.
