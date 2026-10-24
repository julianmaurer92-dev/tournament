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
| 1 | Neues Turnier anlegen und veröffentlichen | 11 | 4 | *wird ergänzt* |
| 2 | Team hinzufügen | 4 | 3 | *wird ergänzt* |
| 3 | Team umbenennen | 5 | 2 | *wird ergänzt* |
| 4 | Team in andere Gruppe verschieben | 5 | 2 | *wird ergänzt* |
| 5 | Spiel starten | 4 | 1 | *wird ergänzt* |
| 6 | Tor eintragen (ohne Torschütze) | 1 | 1 | *wird ergänzt* |
| 7 | **Tor eintragen mit Torschütze** | **9** | **2** | *wird ergänzt* |
| 8 | Spiel beenden und nächstes starten | 5 | 1 | *wird ergänzt* |
| 9 | Anstoßzeit eines Spiels ändern | – | 2 | *wird ergänzt* |
| 10 | Ankündigung senden | 4 | 2 | *wird ergänzt* |
| 11 | Theme wechseln | 4 | 1 | *wird ergänzt* |
| 12 | Startgebühr als bezahlt markieren | 3 | 1 | *wird ergänzt* |
| 13 | Quittung drucken | 4 | 2 | *wird ergänzt* |
| 14 | Spielplan drucken | 3 | 2 | *wird ergänzt* |
| 15 | Zuschauer: Tabelle meiner Gruppe finden | 3 | 1 | *wird ergänzt* |
| 16 | Zuschauer: nächstes Spiel meines Teams finden | 4 | 0–1 | *wird ergänzt* |

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
