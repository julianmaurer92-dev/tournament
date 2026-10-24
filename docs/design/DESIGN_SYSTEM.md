# Anpfiff – das Designsystem von CupPlan

Stand: 25.10.2026 · Branch `ui/neues-design`

---

## Warum „Anpfiff"

Der Name beschreibt nicht nur die Stimmung, sondern das Bauprinzip:
Hier fängt etwas an, und alle schauen hin. Die Klassennamen beginnen
mit `ap-`, die Design-Tokens mit `--ap-`.

Die Richtung entstand aus drei gebauten Proben unter `/design-lab/`.
Sie sind absichtlich stehen geblieben – wer später fragt, warum die
Oberfläche so aussieht und nicht anders, kann die Alternativen noch
einmal nebeneinander sehen.

| Probe | Idee | Ergebnis |
|---|---|---|
| **Tafel** | Anzeigetafel als Bauprinzip: kräftiger Rand, Beschriftungsstreifen oben, Tabellenziffern | **Bauprinzip übernommen** |
| **Kreide** | Spielfeldlinien als Gestaltung, hell auf Grün | **abgelehnt** – ein grüner Hintergrund überall macht die Vereinsfarbe wertlos und zwingt jeden Text auf einen Kontrast-Drahtseilakt. Nur die Linien blieben als Signatur. |
| **Kiosk** | warmes Papierweiß, dicke abgerundete Kacheln, große Ziele | **Ergonomie übernommen** |

Die wichtigste Erkenntnis aus den Proben: **CupPlan hat nicht zwei
Geschmäcker, sondern zwei Betriebsarten.**

---

## Die drei Prinzipien

### 1. Alles ist eine Tafel

Jede Fläche hat einen **Beschriftungsstreifen** oben (gesperrte
Versalien, leise) und darunter den Inhalt. Karten, Tabellen,
Formulare, der Spielstand – eine einzige Grundform.

```html
<section class="ap-tafel">
    <header class="ap-tafel-kopf">Gruppentabelle</header>
    <div class="ap-tafel-inhalt"> … </div>
</section>
```

Das Vorbild ist das einzige Objekt, das am Sportplatz wirklich jeder
ohne Nachdenken liest – die Anzeigetafel.

### 2. Zahlen sind das Gesicht

Spielstand, Uhr, Punkte, Tordifferenz: Das sind die Daten, wegen
derer jemand auf den Bildschirm schaut. Sie bekommen die größte
Schrift, eine **schmale Anzeigeschrift** und **Tabellenziffern**
(`font-variant-numeric: tabular-nums`) – ein Spielstand darf nicht
springen, wenn aus der 1 eine 2 wird.

Alles andere ist Beschriftung.

### 3. Zwei Betriebsarten, ein System

| | **Hell = bedienen** | **Dunkel = zeigen** |
|---|---|---|
| wo | draußen, am Spielfeldrand | im Zelt, auf dem Beamer |
| wann | tagsüber, in der Sonne | abends, bei Kunstlicht |
| wie | eine Hand, Handschuhe | aus zehn Metern |
| Flächen | warm und hell | tief und satt |
| Akzent | gedeckt, kontraststark | leuchtend |

Dieselben Bausteine, andere Werte. Mehr Unterschied braucht es nicht.

**Signatur:** die **Kreidelinie** – dünne, unterbrochene Linien und
die Geometrie des Spielfelds (ein angedeuteter Mittelkreis hinter dem
Live-Spielstand). Nur als Zierde, nie als Träger von Information.

---

## Dateien

| Datei | Inhalt |
|---|---|
| `css/anpfiff.css` | Tokens: Maße, Schrift, Bewegung, Farbrollen, **alle Themes**, Vereinsfarbe, Druck |
| `css/anpfiff-bausteine.css` | Tafel, Knopf, Segment, Abzeichen, Tabelle, Formular, Schalter, leerer Zustand, Skelett, Meldung, Schublade |
| `css/anpfiff-huelle.css` | App-Hülle: Seitenleiste, Kopfzeile, **Leiste unten**, Schutz gegen waagerechtes Scrollen |
| `css/anpfiff-oeffentlich.css` | Live-Ansicht, Handy, Startseite, Speisekarte |
| `css/anpfiff-steuerung.css` | Spielsteuerung |
| `css/anpfiff-beamer.css` | Beamer und Präsentationsmodus |
| `css/anpfiff-galerie.css` | Theme-Galerie |
| `css/anpfiff-palette.css` | Befehlspalette |
| `css/anpfiff-tabler.css` | **Brücke** zu Tabler und zu alten Klassennamen |
| `templates/_anpfiff.html` | Makros: `symbol`, `knopf`, `abzeichen`, `karten`, `leer`, `wappen`, `teamname` |
| `templates/anpfiff_huelle.html` | die App-Hülle als Basisvorlage |
| `js/anpfiff.js` | Meldungen, Rückgängig, Speichern, Schublade, Navigation |

**Live anzusehen:** `/admin/styleguide` – jeder Baustein, jedes Theme,
hell und dunkel umschaltbar.

---

## Tokens

### Farbrollen

Eine Variable sagt, **wozu** ein Wert da ist, nicht welche Farbe er
hat. `--ap-tafel` statt `--grau-800`. Dadurch braucht ein neues Theme
nur rund 18 Werte und wirkt sofort überall.

| Rolle | Bedeutung |
|---|---|
| `--ap-grund` | Hintergrund der Seite |
| `--ap-tafel` | Fläche einer Tafel |
| `--ap-tafel-kopf` | Beschriftungsstreifen oben |
| `--ap-tafel-tief` | eingelassene Flächen (Eingaben) |
| `--ap-kante` | **dekorativer** Rand – darf leise sein |
| `--ap-kante-aktiv` | Rand von **Bedienelementen** – muss 3:1 haben |
| `--ap-schrift-farbe` | Fließtext |
| `--ap-leise` | Nebentext |
| `--ap-still` | Beschriftungen, Einheiten |
| `--ap-akzent` / `-stark` / `-leise` | die Farbe des Themes |
| `--ap-auf-akzent` | Schrift auf der Akzentfläche |
| `--ap-live` | läuft gerade |
| `--ap-tor` | Spielstand, Punkte, Erfolg |
| `--ap-warnung`, `--ap-gefahr` | Achtung, Löschen |
| `--ap-gelb`, `--ap-rot` | **Karten – themenunabhängig** |

> **Die Trennung von `--ap-kante` und `--ap-kante-aktiv` ist kein
> Detail.** Der erste Kontrastlauf meldete 35 Verstöße, weil eine
> einzige Variable gleichzeitig den Zierrand einer Tafel und den Rand
> eines Eingabefelds trug. WCAG 1.4.11 verlangt 3:1 für
> Bedienelemente, nicht für Zierde. Zwei Rollen, Problem weg.

> **Karten sind keine Gestaltungsfrage.** Eine gelbe Karte ist gelb,
> in jedem Theme, sonst versteht sie niemand.

### Maße

Raum in Vielfachen von 4 px (`--ap-raum-1` … `-8`). Bewusst grob: Wer
mit Handschuhen tippt, profitiert nicht von 2-Pixel-Feinheiten.

Berührziele: `--ap-ziel` 48 px, `--ap-ziel-gross` 64 px,
`--ap-ziel-riesig` 84 px (der Tor-Knopf). 44 px ist das Minimum der
Richtlinie; die Hauptaktion bekommt deutlich mehr, weil ein Tor im
Jubel getippt wird, nicht in Ruhe.

### Bewegung

120 / 200 / 320 ms, eine Kurve. Alles, was wackelt, nervt am dritten
Spiel. `prefers-reduced-motion: reduce` schaltet ausnahmslos alles ab.

---

## Themes

Acht eigene Themes, jedes **hell und dunkel**, dazu **Anzeigetafel**
(nur dunkel) und das Druck-Theme.

| Theme | Gedacht für |
|---|---|
| **Rasen** | die Vorgabe – Platzgrün auf warmem Papier |
| **Flutlicht** | kühles Blauweiß, dunkel mit Signalgelb |
| **Trikot** | Vereinsrot, kräftig und laut |
| **Auswärts** | tiefes Blau, ruhig und seriös |
| **Bernstein** | warmes Orange auf Sand – gut bei Sonne |
| **Kreide** | fast farblos, lässt die Vereinsfarben sprechen |
| **Vereinsheim** | Holz und Creme, gemütlich wie der Tresen |
| **Nachtspiel** | beinahe schwarz mit Neongrün, hoher Kontrast |
| **Anzeigetafel** | **nur dunkel** – reines Schwarz, ein leuchtender Akzent, alles eine Nummer größer. Auf dem Beamer die Vorgabe. |
| *Druck* | immer hell und tintensparend, unabhängig vom Bildschirm |

**Alte Namen bleiben gültig.** Zwei Generationen: die englischen
(`dark`, `midnight`, `slate`, `ocean`, `crimson`, `light`, `navy`,
`forest`, `amber`, `violet`) und die deutschen aus der UX-Nachtschicht
(`rasen`, `mitternacht`, `schiefer`, `ozean`, `ziegel`, `forst`,
`bernstein`, `veilchen`, `papier`, `stadion`). Siehe
`app/themes.py` → `ALTE_NAMEN`.

### Kontrast

```
python3 scripts/kontrast_anpfiff.py          # Pflichtpaare
python3 scripts/kontrast_anpfiff.py --alle   # mit Hinweisen
```

Prüft **17 Varianten × 16 Kombinationen = 272 Paare** gegen WCAG 2.1
AA. Rückgabewert 1, wenn eine Pflichtkombination durchfällt – damit
lässt es sich in eine Prüfkette hängen.

Der Prüfer löst `var()`-Verweise auf. Ohne das prüft er die
Zeichenkette statt der Farbe und meldet alles als fehlend.

---

## Ein neues Theme anlegen

Drei Schritte, rund zehn Minuten.

**1. Werte in `app/static/css/anpfiff.css`**, am Ende von Abschnitt 3:

```css
[data-theme="heimspiel"][data-schema="hell"] {
    --ap-grund: #f5f3ef;
    --ap-tafel: #ffffff;
    --ap-tafel-kopf: #ebe7e0;
    --ap-tafel-tief: #f1eee8;
    --ap-kante: #d9d3c8;
    --ap-kante-aktiv: var(--ap-still);   /* Pflicht, sonst 1.4.11 */
    --ap-kreide: #e5e0d6;
    --ap-schrift-farbe: #1f1d1a;
    --ap-leise: #5c574f;
    --ap-still: #6e6860;
    --ap-akzent: #8a3324;
    --ap-akzent-stark: #6d2719;
    --ap-akzent-leise: #f6e3df;
    --ap-auf-akzent: #ffffff;
    --ap-live: #c62828;
    --ap-tor: #11703f;
    --ap-warnung: #8a5a00;
    --ap-gefahr: #b32424;
}
/* … dasselbe für [data-schema="dunkel"] */
```

**2. Eintrag in `app/themes.py` → `THEMES`** mit Name,
Beschreibung und den drei Vorschaufarben (Grund, Tafel, Akzent) je
Schema. Die Galerie liest sie von dort – sie muss nichts aus dem CSS
herausfischen.

**3. Nachrechnen:**

```
python3 scripts/kontrast_anpfiff.py
```

Fällt etwas durch, nennt das Skript die Kombination, die beiden
Farbwerte und den erreichten Wert. Typische Ursachen: `--ap-still`
auf `--ap-tafel-kopf` zu blass, oder `--ap-auf-akzent` passt nicht
zum Akzent (dann die Schriftfarbe wechseln, nicht den Akzent).

Danach steht das Theme in der Galerie und ist überall benutzbar.

---

## Vereinsfarbe

Eine gewählte Akzentfarbe überschreibt den Theme-Akzent. Die
Schriftfarbe darauf rechnet der Server aus (`app/farben.py`):

- `lesbare_schrift()` vergleicht den Kontrast gegen Weiß und gegen
  Schwarz und nimmt den besseren – eine knallgelbe Vereinsfarbe mit
  weißer Schrift wäre unlesbar.
- `taugt_als_akzent()` prüft, ob sich die Farbe überhaupt genug vom
  Hintergrund abhebt. Wenn nicht, bleibt der Theme-Akzent. Eine
  unsichtbare Farbe ist schlimmer als keine.

---

## Fallen, in die ich getappt bin

Damit es dem nächsten nicht genauso geht:

| Symptom | Ursache |
|---|---|
| **Ein Symbol füllt den ganzen Bildschirm** | `<svg>` ohne `viewBox` hat keine Eigengröße. Fehlt dazu die Größenangabe aus dem CSS (alte Klasse!), wächst es auf seinen Container. Das Makro `symbol()` setzt `viewBox` immer. |
| **Symbol in einem Knopf ist null Pixel breit** | Dasselbe in Grün: `viewBox` fehlte, der Knopf ist ein Flex-Eltern, und ein Flex-Element ohne Eigengröße fällt auf null. |
| **Eine Karte ist dunkelblau in einem grünen Theme** | `var(--bg-secondary, #111827)` – ohne Zuordnung schlägt der Ersatzwert durch. Alle alten Namen stehen im Aliasblock in `anpfiff.css`. |
| **Die Seite scrollt waagerecht** | Rasterfelder schrumpfen von Haus aus nicht unter ihre Inhaltsbreite. `min-width: 0` auf die Kinder; breite Tabellen scrollen in ihrer Tafel. |
| **Vorschaufarben kommen als `["`** | `tojson` in einem Attribut mit **doppelten** Anführungszeichen. Die Werte enthalten selbst welche. Einfache nehmen. |
| **Leerzeichen zwischen Symbol und Text verschwindet** | In einem Flex-Eltern werden reine Leerzeichen-Textknoten nicht gerendert. `gap` benutzen oder `margin-right`. |
