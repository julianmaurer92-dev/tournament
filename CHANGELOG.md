# Was sich geändert hat

## UX-Redesign (24.10.2026)

Ein Tag ausschließlich an der Bedienung. Keine neuen Turnierfunktionen –
alles, was CupPlan vorher konnte, kann es weiterhin. Es ist nur schneller
zu erreichen.

Der Leitgedanke: **wenige große, eindeutige Elemente, möglichst wenige
Klicks, und Einstellungen dort, wo man sie braucht.**

---

### Am Spielfeldrand

**Tor mit Torschütze: zwei Tipps statt neun Schritte.**
Vorher: „+" drücken, auf eine eigene Seite wechseln, Ereignisart wählen,
Mannschaft wählen, Spieler wählen, Minute eintippen, das Häkchen
„Spielstand mitzählen" **abwählen** (sonst zählte das Tor doppelt),
abschicken. Jetzt: Tipp auf das große **+**, Tipp auf den Spielernamen.
Zuletzt eingetragene Schützen stehen oben.

**Der Spielstand steht sofort im Bild**, ohne auf den Rundruf zu warten.
Im Sportheim-WLAN konnte das dauern – und wer nichts passieren sah,
tippte noch einmal.

**Alles passt ohne Scrollen auf ein Handy**, auch mit zwei Spielfeldern.
Vorher waren es 1932 Pixel Inhalt auf 844 Pixel Bildschirm.

**Keine Bestätigungsdialoge mehr.** Jede Aktion lässt sich zurücknehmen –
über den Hinweis unten am Bildschirm oder mit `Strg/Cmd + Z`. Ein Dialog
am Spielfeldrand hält die ganze Seite an, auch die Live-Aktualisierung.

**Die Uhr zeigt ihren Zustand über die Farbe:** läuft, letzte Minute,
letzte 30 Sekunden, abgelaufen.

**Fällt die Verbindung aus, steht das oben auf der Seite** – vorher nur
in der Browserkonsole, die am Spielfeldrand niemand offen hat.

Am Schreibtisch: `Leertaste` pfeift an, `Q` und `P` sind die Tore links
und rechts.

---

### Überall im Adminbereich

**Ein Menü statt elf verschiedener.** Vorher trug jede Seite ihr eigenes:
die Turnierliste zeigte „Benutzer · Speisekarte · Export", das Dashboard
„Design · Spielplan · Org", die Spielsteuerung nur „Ereignisse ·
Dashboard". Welche Bereiche es überhaupt gibt, stand nirgends
vollständig. Jetzt: eine feste Seitenleiste mit Turnier-Umschalter und
immer denselben acht Bereichen. Auf dem Handy fährt sie als Schublade
aus.

**Suche über alles: `Strg/Cmd + K`.** Namen tippen, Enter. Findet Seiten,
Aktionen (drucken, Live-Ansicht, Anmeldeformular), alle Mannschaften,
alle Spiele und alle Themes. Auch unter Wörtern, die nirgends im Menü
stehen: „spielzeit", „startgeld", „backup", „anzeigetafel". `?` zeigt
alle Tastenkürzel.

**Turnier-Einstellungen an einer Stelle.** Spielfelder, Spielzeit,
Verlängerung und „Was Zuschauer sehen" standen vorher auf zwei Seiten
verteilt, die beiden Haken sogar doppelt. Jetzt stehen sie in einer
Karte und speichern sofort.

---

### Aussehen

**Zehn Themes, jedes hell und dunkel** – von „Rasen" (Vorgabe) über
„Papier" (sehr hell, für den Beamer bei Tageslicht) bis „Stadion"
(höchster Kontrast für große Entfernung). **Ein Klick wechselt**, und man
sieht sofort, worauf man sich einlässt: Jede Karte in der Galerie zeigt
eine Miniatur der echten Oberfläche.

Alle zwanzig Varianten sind gegen den Barrierefreiheits-Standard
**WCAG AA** nachgerechnet, nicht nur behauptet.

**Die Vereinsfarbe** überschreibt den Theme-Akzent. Die Schriftfarbe
darauf wählt CupPlan selbst nach Kontrast – eine knallgelbe Vereinsfarbe
mit weißer Schrift wäre unlesbar. Hebt sich die Farbe zu wenig vom
Hintergrund ab, bleibt der Theme-Akzent.

**Einheitliche Symbole statt Emoji.** Vorher waren 339 Emoji und
HTML-Zeichen quer durch die Oberfläche verstreut. Die sehen auf jedem
Gerät anders aus, lassen sich nicht einfärben und passen in keiner Größe
zum Text daneben.

**Der Ausdruck ist immer hell und tintensparend**, unabhängig vom
gewählten Theme.

---

### Auf dem Beamer

**„Präsentieren" – ein Klick.** Danach läuft die Anzeige allein: Live
(20 s) → Tabellen (15 s) → Spielplan (15 s), jeweils über die volle
Breite und in Beamer-Schriftgröße. Vorher standen immer alle drei
Spalten gleichzeitig nebeneinander; aus zehn Metern las das niemand.

`←` `→` blättern von Hand, `Leertaste` hält an, `Esc` beendet.

**Die Beamer-Ansicht folgt jetzt dem gewählten Theme.** Vorher war sie
fest dunkelblau – in einem hellen Zelt die schlechteste aller
Möglichkeiten.

**Läuft gerade kein Spiel**, steht groß da, welches als Nächstes kommt,
mit Uhrzeit, Spielfeld und Gruppe – statt „Kein Spiel aktiv".

---

### Für Zuschauer

**„Mein Team" merken.** Einmal die Mannschaft wählen – danach steht beim
Öffnen der Handy-Ansicht ganz oben, wann und wo das nächste Spiel ist,
mit Gegner, Uhrzeit, Spielfeld und Gruppe. Läuft gerade eines, steht es
darüber mit Spielstand. Die Wahl liegt nur im eigenen Browser; kein
Konto, keine Daten auf dem Server.

**Mannschaftsnamen werden nicht mehr getrennt.** Vorher stand in
schmalen Spalten „SpVgg Hohen-berg" oder „TSV Metten-berg" – der Browser
trennte Vereinsnamen wie Fließtext.

---

### Behobene Fehler

- **Vier von zehn Themes ließen sich nicht speichern.** `navy`, `forest`,
  `amber` und `violet` standen in der Auswahl, wurden beim Speichern aber
  stillschweigend verworfen. Man klickte, und es passierte nichts.
- **„Tabelle ausblenden" sprang von selbst wieder an.** Wer die Tabelle
  verborgen hatte und danach irgendetwas an den Turnierdaten änderte –
  Datum, Uhrzeit, Beschreibung –, hatte sie wieder öffentlich im Netz,
  ohne es zu merken.
- **Lange Turniernamen** drückten in der Handy-Kopfzeile die Knöpfe
  daneben zusammen.
