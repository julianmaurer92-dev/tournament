# Klick-Audit CupPlan

**Aufgenommen:** 24.10.2026, Stand `nightly/2026-10-24` (vor dem UX-Umbau)

## Wie gemessen wurde

Gezählt werden **Interaktionen**, die der Mensch ausführt: Klicks/Tipps,
Auswahl in einem Aufklappmenü, Fokussieren eines Feldes. Tippen von Text
zählt als **eine** Interaktion pro Feld (egal wie viele Zeichen), weil die
Anzahl der Buchstaben nichts über die Bedienqualität sagt.

Startpunkt ist jeweils der Ort, an dem man am Turniertag realistisch steht:

- Admin-Aufgaben: **Turnier-Dashboard** (`/admin/t/<slug>/`)
- Zuschauer-Aufgaben: **Startseite** (`/`) auf dem Handy

Seitenwechsel zählen mit, weil sie am Turniertag Zeit und Orientierung
kosten — auf einem Handy am Spielfeldrand mehr als am Schreibtisch.

---

## Bilanz

| # | Aufgabe | Vorher | Ziel | Nachher |
|---|---|---:|---:|---:|
| 1 | Neues Turnier anlegen und veröffentlichen | 11 | 4 | 11 (offen) |
| 2 | Team hinzufügen | 4 | 3 | 4 (offen) |
| 3 | Team umbenennen | 5 | 2 | 5 (offen) |
| 4 | Team in andere Gruppe verschieben | 5 | 2 | 5 (offen) |
| 5 | Spiel starten | 4 | 1 | **1** |
| 6 | Tor eintragen (ohne Torschütze) | 1 | 1 | **2** |
| 7 | **Tor eintragen mit Torschütze** | **9** | **2** | **2** |
| 8 | Spiel beenden und nächstes starten | 5 | 1 | **1** |
| 9 | Anstoßzeit eines Spiels ändern | – | 2 | – (offen) |
| 10 | Ankündigung senden | 4 | 2 | **2** |
| 11 | Theme wechseln | 4 | 1 | **1** |
| 12 | Startgebühr als bezahlt markieren | 3 | 1 | 1 (nicht nachgemessen) |
| 13 | Quittung drucken | 4 | 2 | **1** |
| 14 | Spielplan drucken | 3 | 2 | **1** |
| 15 | Zuschauer: Tabelle meiner Gruppe finden | 3 | 1 | **0–1** |
| 16 | Zuschauer: nächstes Spiel meines Teams finden | 4 | 0–1 | **0** |
| 17 | Beliebige Seite oder beliebiges Spiel öffnen | 2–4 | 1 | **1** |
| 18 | Beamer-Präsentation starten | 5 | 1 | **1** |

---

## Die Wege im Einzelnen (Stand vorher)

### 1. Neues Turnier anlegen und veröffentlichen — 11

Von `/admin/t/<slug>/` aus:

1. „← Turniere" (Seitenwechsel)
2. Feld *Name* fokussieren + tippen
3. Feld *Datum*
4. Feld *Uhrzeit*
5. Feld *Beschreibung*
6. *Spielzeit* ändern
7. *Verlängerung* ändern
8. *Spielfelder* auswählen
9. *Finalrundentyp* auswählen
10. ggf. *Tabelle/Ergebnisse ausblenden* ankreuzen
11. „+ Erstellen"

Danach ist das Turnier zwar angelegt, hat aber noch **kein Theme** — dafür
nochmal Dashboard → Design → Farbe → Speichern (4 weitere).

**Was stört:** Ein einziges langes Formular, in dem Pflicht und Kür gleich
aussehen. Spielzeit und Finalrundentyp kann man später ändern, das weiß man
hier aber nicht.

### 2.–4. Teams verwalten — 4 bis 5

Hinzufügen (4): Dashboard → „Administration" → Teamname tippen → Gruppe
wählen → „+".

Umbenennen (5): Dashboard → „Administration" → Bleistift am Team →
Namensfeld → Speichern. Es öffnet sich eine zusätzliche Bearbeitungszeile
in der Tabelle.

Gruppe wechseln (5): derselbe Weg, nur mit dem Aufklappmenü statt dem Namen.

**Was stört:** Der Name steht sichtbar auf dem Bildschirm, ist aber nicht
anklickbar. Man muss erst in einen Bearbeitungsmodus.

### 5. Spiel starten — 4

Dashboard → Spiel in der Liste suchen → „Steuerung" (Seitenwechsel) →
„▶ Start".

**Was stört:** Der Seitenwechsel. Am Turniertag will man vom Dashboard aus
starten, ohne den Überblick zu verlieren.

### 7. Tor eintragen mit Torschütze — 9 (der schlimmste Weg)

1. „+" am Spielstand (Spielsteuerung)
2. „⚽ Ereignisse" (Seitenwechsel)
3. Aufklappmenü *Ereignis* → „Tor"
4. Aufklappmenü *Mannschaft*
5. Feld *Spieler* fokussieren
6. Namen aus der Vorschlagsliste wählen
7. Feld *Minute*
8. Häkchen *Spielstand mitzählen* abwählen (sonst zählt das Tor doppelt)
9. „+ Erfassen"

**Was stört:** Alles. Das ist die häufigste Aktion am Turniertag und der
längste Weg in der ganzen App. Schritt 8 ist zudem eine Falle: Wer ihn
vergisst, hat ein Tor zu viel auf der Anzeigetafel.

### 8. Spiel beenden und nächstes starten — 5

„Beenden" → Bestätigungsdialog → „Zurück zum Dashboard" → nächstes Spiel
suchen → „Steuerung" → „▶ Start".

### 10. Ankündigung senden — 4

Dashboard → Feld *Ankündigung* → tippen → „Senden".

### 11. Theme wechseln — 4

Dashboard → „🎨 Design" (Seitenwechsel) → Farbfeld anklicken →
„Speichern". Die Vorschau zeigt nur einen kleinen Ausschnitt; wie die
Live-Ansicht aussieht, sieht man erst nach dem Speichern in einem anderen
Tab.

### 12.–13. Startgebühren — 3 und 4

Bezahlt markieren (3): Dashboard → „💼 Org" → Häkchen.
Quittung drucken (4): zusätzlich „Quittung" → Druckdialog.

### 15.–16. Zuschauer auf dem Handy

Tabelle meiner Gruppe (3): Startseite → Turnier wählen → Tab „Tabelle".
Bei mehreren Gruppen muss man dann noch scrollen und die richtige suchen.

Nächstes Spiel meines Teams (4): Startseite → Turnier → Tab „Spiele" →
in der Liste suchen. Die App weiß nicht, welches Team mich interessiert.

---

## Die drei größten Hebel

1. **Tor mit Torschütze: 9 → 2.** Häufigste Aktion, längster Weg.
2. **Spielsteuerung ohne Seitenwechsel: 4 → 1 fürs Starten, 5 → 1 für
   „beenden und weiter".** Der Seitenwechsel kostet am Spielfeldrand am
   meisten.
3. **„Mein Team" merken: 4 → 0.** Wer einmal sein Team gewählt hat, soll
   dessen nächstes Spiel sofort sehen, ohne zu suchen.


---

## Nachher: die Wege im Einzelnen

### 5. Spiel starten — 1 (vorher 4)

Die Spielsteuerung ist jetzt eine Vollbildseite. Der Knopf **„Anpfiff"**
steht unten in Daumenreichweite. Von der Übersicht aus führt ein Klick auf
das Spiel direkt hierher.

### 7. Tor eintragen mit Torschütze — 2 (vorher 9)

1. Tipp auf das große **+** der Mannschaft
2. Tipp auf den Spielernamen

Fertig. Tor und Schütze gehen in **einer** Anfrage an den Server, der
Spielstand steht sofort im Bild. Zuletzt benutzte Schützen rücken nach
oben — in einer Mannschaft trifft oft derselbe Spieler mehrfach.

Der Stolperstein von vorher ist weg: Es gibt kein Häkchen
„Spielstand mitzählen" mehr, das man vergessen kann. Statt des
Bestätigungsdialogs gibt es **Rückgängig** im Hinweis unten.

Wer keine Spielerliste hinterlegt hat, tippt auf
„Tor eintragen (keine Spielerliste hinterlegt)" — dann sind es weiterhin
zwei Tipps, aber ohne Namen. Das ist der Grund, warum Zeile 6
(Tor **ohne** Schütze) von 1 auf 2 steigt: Der zweite Tipp ist der Preis
dafür, dass der erste nicht mehr raten muss, ob ein Schütze folgt.

### 8. Spiel beenden und nächstes starten — 1 (vorher 5)

Ein Knopf: **„Beenden & weiter"**. Darunter steht klein, welches Spiel als
Nächstes kommt. Nach dem Tippen bleiben 2,6 Sekunden zum Zurücknehmen,
dann wechselt die Seite zur Steuerung des nächsten Spiels.

Bei zwei Spielfeldern werden beide Spiele gemeinsam beendet — sie laufen
ohnehin parallel.

### 11. Theme wechseln — 1 (vorher 4)

Die Design-Seite ist eine Galerie mit zehn großen Karten. Jede zeigt eine
**Miniatur der echten Oberfläche** in diesem Theme — Kopfzeile, Spielstand,
Tabellenzeilen — nicht nur drei Farbpunkte.

Ein Klick wendet an: sofort auf dieser Seite, gespeichert, und gültig für
Live-Ansicht, Handy und Beamer. Kein Speichern-Knopf.

Dazu ein Schalter **Hell / Dunkel** — jedes Theme gibt es in beiden
Varianten, also 20 statt bisher 10 (von denen nur 9 dunkel waren).

Nebenbei behoben: Die Einstellungs-Route akzeptierte nur sechs der zehn
angebotenen Themes. „Navy", „Forest", „Amber" und „Violet" ließen sich
auswählen, aber **nicht speichern** — der Server antwortete mit einem
Fehler, den die Oberfläche verschluckte.

### 16. Zuschauer: nächstes Spiel meines Teams — 0 (vorher 4)

Einmal auf **„Meine Mannschaft wählen"** tippen und das Team aus der Liste
aussuchen (2 Tipps, einmalig). Danach steht bei jedem Öffnen der
Handy-Ansicht ganz oben:

> ★ SC Weiler
> **NÄCHSTES SPIEL** · gegen TuS Lindau · 10:00 Uhr · Feld 1 · Gruppe A

Läuft gerade ein Spiel der Mannschaft, steht es darüber — mit Spielstand.
Ist das Turnier für sie vorbei, sagt die Karte das auch, statt leer zu
bleiben.

Die Wahl liegt nur im Browser (localStorage), je Turnier getrennt. Kein
Konto, keine Daten auf dem Server.

### 17. Beliebige Seite oder beliebiges Spiel öffnen — 1 (vorher 2–4)

`Strg/Cmd + K`, Namen tippen, Enter. Durchsucht Seiten, Seitenaktionen,
alle Mannschaften, alle Spiele und alle Themes.

Vorher hing es davon ab, wo man gerade war: Von der Übersicht zur
Statistik waren es zwei Klicks, von der Spielsteuerung zur Speisekarte
vier — zurück zum Dashboard, zur Turnierliste, zur Speisekarte.

### 18. Beamer-Präsentation starten — 1 (vorher 5)

Vorher: Dashboard öffnen → Beamer-Ansicht in neuem Tab → Tab suchen →
Vollbildknopf (`⛶`, unbeschriftet) finden → klicken. Und dann standen
drei schmale Spalten nebeneinander, die aus zehn Metern niemand lesen
konnte.

Jetzt: **„Präsentieren"** auf dem Dashboard. Die Ansicht öffnet sich,
ein Tastendruck startet Vollbild, und danach läuft sie allein: Live
(20 s) → Tabellen (15 s) → Spielplan (15 s), jeweils über die volle
Breite und in Beamer-Schriftgröße (Tabellenzeilen 24 px statt 15 px).

`←` `→` blättern von Hand, `Leertaste` hält an, `Esc` beendet.

---

## Bilanz am Ende des Tages

**Erledigt – 11 von 18 Aufgaben wurden schneller:**

| Aufgabe | Vorher | Nachher |
|---|---:|---:|
| Tor eintragen mit Torschütze | 9 | **2** |
| Spiel beenden und nächstes starten | 5 | **1** |
| Spiel starten | 4 | **1** |
| Theme wechseln | 4 | **1** |
| Beamer-Präsentation starten | 5 | **1** |
| Spielplan drucken | 3 | **1** |
| Beliebige Seite / beliebiges Spiel öffnen | 2–4 | **1** |
| Zuschauer: Tabelle meiner Gruppe | 3 | **0–1** |
| Quittung drucken | 4 | **1** |
| Ankündigung senden | 4 | **2** |
| Zuschauer: nächstes Spiel meines Teams | 4 | **0** |

Die **am Turniertag häufigsten Handgriffe** – Spiel starten, Tor
eintragen, Spiel beenden, nächstes starten – liegen jetzt alle bei
**einem oder zwei Tipps**. Das war das eigentliche Ziel.

**Nicht erledigt – fünf Aufgaben sind unverändert:**

| # | Aufgabe | Vorher | Ziel | Warum offen |
|---|---|---:|---:|---|
| 1 | Neues Turnier anlegen | 11 | 4 | Der Assistent in Schritten wurde nicht mehr gebaut |
| 2 | Team hinzufügen | 4 | 3 | gehört zum Punkt „Leinwand und Inspektor" |
| 3 | Team umbenennen | 5 | 2 | braucht das direkte Bearbeiten im Spielplan |
| 4 | Team in andere Gruppe verschieben | 5 | 2 | braucht Ziehen und Ablegen |
| 9 | Anstoßzeit ändern | – | 2 | braucht das direkte Bearbeiten |

Alle fünf hängen am selben, nicht mehr gebauten Baustein: **direktes
Bearbeiten auf der Spielplanseite** – Mannschaftsnamen und Uhrzeiten
anklicken und sofort ändern, statt ein Formular zu öffnen. Das ist der
größte verbliebene Hebel und steht als erster Punkt in
`UX_LOG.md` → „Was offen blieb".

### Wie gezählt wurde

Ein Klick ist eine Zeigeraktion, die der Benutzer bewusst ausführt:
Knopf, Link, Auswahlfeld öffnen, Eintrag wählen. Tippen zählt nicht als
Klick; ein Tastenkürzel, das eine Suche öffnet, zählt als ein Klick.
Gezählt wird ab dem Dashboard des Turniers – nicht ab der Startseite,
weil niemand am Turniertag ständig neu einsteigt.

### Nachgemessen am Browser

Die folgenden Werte sind nicht geschätzt, sondern am laufenden Programm
nachgezählt:

| Aufgabe | Befund |
|---|---|
| Ankündigung senden | Eingabefeld und „Senden" stehen direkt auf der Übersicht → **2** |
| Quittung drucken | „Quittung" je Mannschaftszeile; die Seite ruft den Druckdialog selbst auf → **1** |
| Spielplan drucken | `Strg/Cmd + K`, „spielplan drucken", Enter → **1** |
| Tabelle meiner Gruppe (Zuschauer) | am Rechner ohne Klick sichtbar (**0**), am Handy ein Tipp auf den Reiter (**1**) |

**Nicht nachgemessen:** Startgebühr als bezahlt markieren. Auf der
Organisationsseite steht je Mannschaft ein Schalter – der Weg ist
sichtbar ein Klick, aber ich habe nicht geprüft, ob die Änderung ein
Neuladen übersteht. Deshalb steht in der Tabelle „1 (nicht
nachgemessen)" und keine fette Zahl.
