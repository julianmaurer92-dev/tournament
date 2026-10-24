# Ressourcen und Lizenzen

Stand: 25.10.2026 · Branch `ui/neues-design`

Alle Fremdressourcen stehen unter einer Lizenz, die **kommerzielle
Nutzung erlaubt**. Alles liegt **lokal im Projekt** unter
`app/static/` – CupPlan ruft im Betrieb keinen fremden Server auf.

---

## Warum selbst hosten

1. **Turniertag.** Die Beamer-Ansicht im Zelt hängt oft an einem
   schwachen Hotspot. Fällt das Internet aus, während das lokale Netz
   noch steht, muss CupPlan trotzdem vollständig aussehen.
2. **Datenschutz.** Ein Abruf bei Google Fonts überträgt die
   IP-Adresse jedes Zuschauers an einen Dritten. Dafür bräuchte es
   eine Einwilligung, die niemand einholt.
3. **Tempo.** Eine zusätzliche Verbindung zu einem fremden Server
   kostet auf einem Handy im Mobilfunknetz mehr Zeit als die Datei
   selbst.

---

## Schriften

Drei Schriften, drei klare Aufgaben. Alle **SIL Open Font License
1.1**, alle als `woff2`, alle nur in den lateinischen Schnitten.

### Bricolage Grotesque — Anzeige

| | |
|---|---|
| **Aufgabe** | Überschriften, Markenauftritt, Mannschaftsnamen auf der Bühne |
| **Version** | v9 (Google-Fonts-Auslieferung, abgerufen 24.10.2026) |
| **Autor** | Atelier Triay |
| **Lizenz** | SIL OFL 1.1 → `lizenzen/bricolage-grotesque-OFL.txt` |
| **Quelle** | https://github.com/ateliertriay/bricolage |
| **Im Projekt** | `vendor/fonts/bricolage-400800-latin*.woff2` (188 KB, variabel 400–800) |

Gewählt, weil sie **sofort wiedererkennbar** ist: etwas breiter, etwas
eigenwillig, deutlich moderner als die üblichen Grotesken. Genau das,
was eine eigene Design-Sprache braucht – und als variable Schrift
deckt eine Datei alle Gewichte ab.

### Barlow Condensed — Zahlen

| | |
|---|---|
| **Aufgabe** | Spielstand, Uhr, Punkte, Tabellenspalten |
| **Version** | v13 |
| **Autor** | Jeremy Tribby |
| **Lizenz** | SIL OFL 1.1 → `lizenzen/barlow-OFL.txt` |
| **Quelle** | https://github.com/jpt/barlow |
| **Im Projekt** | `vendor/fonts/barlow-condensed-{600,700,800}-latin*.woff2` (120 KB) |

Eine schmale Schrift bringt bei gleicher Breite **mehr Zeichenhöhe** –
auf einem Beamer aus zehn Metern zählt genau das. Außerdem hat sie
echte Tabellenziffern: Ein Spielstand springt nicht, wenn aus der 1
eine 2 wird.

### Inter — Fließtext

| | |
|---|---|
| **Aufgabe** | alles zum Lesen |
| **Version** | v20 |
| **Autor** | Rasmus Andersson |
| **Lizenz** | SIL OFL 1.1 → `../ux/lizenzen/inter-OFL.txt` |
| **Quelle** | https://rsms.me/inter/ |
| **Im Projekt** | `vendor/fonts/inter-00..06.woff2` (224 KB) |

War bereits im Projekt. Für Bildschirme gezeichnet, in kleinen Größen
die lesbarste der freien Grotesken.

**Zusammen 502 KB** für drei Schriften – im Browser-Cache nach dem
ersten Aufruf.

**Für Apple-Geräte** wird in der Schriftkette `-apple-system,
BlinkMacSystemFont, system-ui` als Rückfall genannt. Das ist ein
Verweis auf die Systemschrift, **keine mitgelieferte Datei**.

---

## Symbole

| | |
|---|---|
| **Name** | Tabler Icons |
| **Version** | 3.26.0 |
| **Autor** | Paweł Kuna |
| **Lizenz** | MIT → `../ux/lizenzen/tabler-icons-MIT.txt` |
| **Quelle** | https://tabler.io/icons |
| **Im Projekt** | `vendor/tabler-sprite.svg` – 63 Symbole, 13 KB |

Ein Sprite statt 63 Einzelabrufen. Alle Symbole nehmen die Textfarbe
an (`currentColor`) und funktionieren dadurch in allen 17
Theme-Varianten ohne eigene Fassung.

**Keine Emoji als Symbole.** Emoji werden vom Betriebssystem
gezeichnet, nicht von CupPlan: Der Pokal sieht auf Windows anders aus
als auf Android, die Größe passt zu keiner Schrift, und einfärben
lassen sie sich gar nicht.

---

## Farben

Die neun Themes sind **selbst entworfen**, nicht aus einer fremden
Palette übernommen. Als Orientierung für Helligkeitsabstufungen
dienten die Prinzipien offener Farbsysteme (Radix Colors, Open
Props) – übernommen wurde die Idee abgestufter Skalen, kein
Farbwert.

Nachrechnen: `python3 scripts/kontrast_anpfiff.py`

---

## Bibliotheken (schon vorher im Projekt)

| Name | Version | Lizenz | Zweck |
|---|---|---|---|
| Tabler CSS/JS | 1.0.0-beta21 | MIT | Grundraster auf noch nicht umgebauten Adminseiten |
| Socket.IO Client | 4.7.5 | MIT | Live-Aktualisierung |
| SortableJS | 1.15.6 | MIT | Reihenfolge per Ziehen |

Alle lokal unter `app/static/vendor/`.

**Keine neue Bibliothek hinzugefügt.** Kein Tailwind, kein Alpine,
kein htmx, kein daisyUI – der Auftrag erlaubt sie ausdrücklich, aber
jede hätte Bauaufwand oder Gewicht gebracht, ohne etwas zu lösen, was
hier nicht ohne sie ging. Das gesamte Designsystem sind rund 3 150
Zeilen eigenes CSS und 1 100 Zeilen eigenes JavaScript, ohne
Bauschritt.

---

## Keine Apple-Materialien

Keine SF-Pro-Dateien, keine SF Symbols, keine Keynote-Grafiken, kein
Apple-Logo und kein Apple-Markenname in der Oberfläche. Der Verweis
auf `-apple-system` in der Schriftkette ist ein Rückfall auf die
Systemschrift des Geräts, keine mitgelieferte Datei.
