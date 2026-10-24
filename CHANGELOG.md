# Was sich geändert hat

## Neues UI – „Anpfiff" (25.10.2026)

CupPlan sieht komplett anders aus. **Es kann genau dasselbe wie
vorher** – alle 113 Seiten und Aktionen funktionieren weiter, nichts
ist weggefallen. Nur die Oberfläche ist neu.

Die Gestaltungssprache heißt **Anpfiff** und folgt drei Gedanken:

**Alles ist eine Tafel.** Jede Fläche hat einen Beschriftungsstreifen
oben und darunter den Inhalt – wie eine Anzeigetafel. Das ist das
einzige Objekt am Sportplatz, das wirklich jeder ohne Nachdenken
liest.

**Zahlen sind das Gesicht.** Spielstand, Uhr und Punkte bekommen die
größte Schrift und eine eigene, schmale Anzeigeschrift. Alles andere
ist Beschriftung.

**Zwei Betriebsarten.** Hell heißt *bedienen* – draußen, in der Sonne,
mit einer Hand. Dunkel heißt *zeigen* – im Zelt, auf dem Beamer,
abends.

---

### Am Spielfeldrand

**Die Spielsteuerung ist komplett neu.** Der Tor-Knopf ist jetzt der
größte Knopf der ganzen App: volle Breite, 84 Pixel hoch. Ein Tipp
öffnet die Spielerliste von unten, ein zweiter trägt Tor und
Torschützen ein. Zuletzt eingetragene Schützen stehen oben – im selben
Spiel trifft oft derselbe mehrfach.

**Alles passt auf ein Bild**, auch mit zwei Spielfeldern gleichzeitig.
Kein Scrollen, kein Umschalten – wer scrollen muss, verpasst das
nächste Tor.

**Die Uhr zeigt ihren Zustand über die Farbe:** bereit, läuft, letzte
Minute, letzte 30 Sekunden (blinkt), abgelaufen. Kein Wort daneben,
das man erst lesen muss.

**Keine Bestätigungsdialoge.** Alles lässt sich mit einem Tipp
zurücknehmen. Ein Dialog hält am Spielfeldrand die ganze Seite an –
auch die Live-Aktualisierung.

**Fällt die Verbindung aus**, steht das als roter Streifen oben auf der
Seite.

---

### Auf dem Handy

**Die Bedienleiste ist nach unten gewandert.** Am Spielfeldrand hält
man das Gerät in einer Hand; was oben klebt, erreicht der Daumen
nicht. Fünf Ziele unten, alles Weitere hinter „Mehr".

Das gilt im Adminbereich genauso wie in der Zuschaueransicht. Ein
pulsender Punkt am Reiter „Live" zeigt, dass gerade ein Spiel läuft.

---

### Für Zuschauer

**Das laufende Spiel ist eine Bühne:** volle Breite, Spielstand so
groß wie der Platz hergibt, dahinter ein angedeuteter Mittelkreis in
Kreideoptik.

Laufen zwei Partien gleichzeitig, stehen sie am Rechner nebeneinander
und auf dem Handy untereinander – vorher wurden die Mannschaftsnamen
auf schmalen Bildschirmen zu Brei.

---

### Auf dem Beamer

**„Präsentieren" – ein Klick**, danach läuft die Anzeige allein: Live,
Tabellen, Spielplan im Wechsel, jeweils über die volle Breite.
Pfeiltasten blättern von Hand, Leertaste hält an, Esc beendet.

**Neues Theme „Anzeigetafel"**, auf dem Beamer die Vorgabe: reines
Schwarz, ein leuchtender Akzent, alles eine Nummer größer. Gebaut für
zehn Meter Abstand. Wer ein eigenes Theme gewählt hat, bekommt
seines – die Entscheidung gehört dem Verein.

---

### Aussehen

**Neun Themes**, acht davon in hell und dunkel: Rasen (die Vorgabe),
Flutlicht, Trikot, Auswärts, Bernstein, Kreide, Vereinsheim,
Nachtspiel und Anzeigetafel.

**Ein Klick wechselt**, sofort und überall – Adminbereich,
Live-Ansicht, Handy und Beamer. Jede Karte in der Galerie zeigt eine
**Miniatur der echten Oberfläche**, nicht nur einen Farbfleck.

Alle 17 Varianten sind gegen den Barrierefreiheits-Standard **WCAG AA**
nachgerechnet, nicht behauptet. 272 Farbkombinationen, nachprüfbar mit
einem Befehl.

**Alte Theme-Namen funktionieren weiter** – beide Generationen. Wer
irgendwann „Midnight" oder „Papier" gespeichert hat, bekommt etwas
Sinnvolles und keinen Fehler.

**Drei neue Schriften**, alle frei lizenziert und lokal im Projekt:
Bricolage Grotesque für Überschriften, Barlow Condensed für alle
Zahlen, Inter für den Fließtext. CupPlan ruft im Betrieb keinen
fremden Server auf – wichtig am Turniertag, wenn das Internet im Zelt
schwächelt.

**Der Ausdruck ist immer hell und tintensparend**, unabhängig vom
Bildschirm.

---

### Behobene Fehler

- **Ein Fußball-Symbol füllte auf dem Beamer den ganzen Bildschirm**
  als schwarze Fläche.
- **Symbole in Knöpfen waren unsichtbar dünn** – sie waren da, aber
  auf null Pixel Breite zusammengedrückt.
- **Mannschaftswappen blähten sich auf** – auf dem Handy war das
  Wappen dreimal so hoch wie der Name daneben.
- **Gruppentabellen ragten aus ihrer Karte heraus.**
- **Die Seite ließ sich seitwärts schieben** – auf dem Handy das
  Ärgerlichste, was passieren kann.
- **Auf dem Handy war die halbe Übersicht unerreichbar**, weil sie
  gegen eine feste Kopfzeilenhöhe rechnete.

---

### Für Entwickler

- Styleguide unter `/admin/styleguide` – jeder Baustein in jedem Theme
- Die drei verworfenen Entwurfsrichtungen stehen unter `/design-lab/`
- `docs/design/DESIGN_SYSTEM.md` – Prinzipien, Tokens, Bausteine, und
  wie man ein neues Theme anlegt
- `docs/design/FUNKTIONEN.md` – die Prüfliste aller 113 Routen
- Keine neue Bibliothek, kein Bauschritt
