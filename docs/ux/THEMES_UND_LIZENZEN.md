# Themes, Schriften, Icons – Herkunft und Lizenzen

Stand: 24.10.2026, Branch `ux/keynote-redesign`

Alle verwendeten Fremdressourcen stehen unter einer Lizenz, die
kommerzielle Nutzung erlaubt. Alles liegt **lokal im Projekt** unter
`app/static/` – CupPlan ruft im Betrieb keinen fremden Server auf.

---

## Warum selbst hosten

Drei Gründe, in dieser Reihenfolge:

1. **Turniertag.** Die Beamer-Ansicht im Zelt hängt oft an einem schwachen
   Hotspot. Fällt das Internet aus, während das lokale Netz noch steht,
   muss CupPlan trotzdem vollständig aussehen.
2. **Datenschutz.** Ein Abruf bei Google Fonts überträgt die IP-Adresse
   jedes Zuschauers an einen Dritten. Dafür bräuchte es eine Einwilligung,
   die niemand einholt.
3. **Tempo.** Eine zusätzliche Verbindung zu einem fremden Server kostet
   auf einem Handy im Mobilfunknetz mehr Zeit als die Datei selbst.

---

## Schrift

| | |
|---|---|
| **Name** | Inter |
| **Version** | v20 (Google-Fonts-Auslieferung, abgerufen 24.10.2026) |
| **Autor** | Rasmus Andersson |
| **Lizenz** | SIL Open Font License 1.1 → `lizenzen/inter-OFL.txt` |
| **Quelle** | https://rsms.me/inter/ · https://github.com/rsms/inter |
| **Im Projekt** | `app/static/vendor/inter.css` + `app/static/vendor/fonts/inter-00..06.woff2` |
| **Umfang** | 7 woff2-Dateien, zusammen rund 218 KB, nur die benötigten Unicode-Bereiche |

Inter ist für Bildschirme gezeichnet und hat echte Tabellenziffern
(`tabular-nums`). Das ist hier kein Detail: Ein Spielstand oder eine
laufende Uhr darf nicht hin- und herspringen, wenn sich eine Ziffer ändert.

**Nicht verwendet:** SF Pro, San Francisco oder andere Apple-Schriften.
Die Lizenz erlaubt den Einsatz in einer Web-App nicht.

---

## Icons

| | |
|---|---|
| **Name** | Tabler Icons |
| **Version** | 3.26.0 |
| **Autor** | Paweł Kuna |
| **Lizenz** | MIT → `lizenzen/tabler-icons-MIT.txt` |
| **Quelle** | https://tabler.io/icons |
| **Im Projekt** | `app/static/vendor/tabler-sprite.svg` |
| **Umfang** | 63 Symbole, 13 KB – nur die tatsächlich verwendeten |

Tabler Icons passt zum bereits vorhandenen Tabler-CSS im Adminbereich,
ist durchgängig im Umriss-Stil gezeichnet und nimmt die Textfarbe an
(`currentColor`). Dadurch funktioniert jedes Symbol in allen 20
Theme-Varianten ohne eigene Fassung.

**Was ersetzt wurde:** Emoji und HTML-Entities, die quer durch die
Vorlagen verstreut waren (`&#9917;` Fußball, `&#127942;` Pokal,
`&#128438;` Drucker und so weiter). Emoji sehen auf jedem Betriebssystem
anders aus, lassen sich nicht einfärben und passen in keiner Größe zum
Text daneben.

Stand jetzt: **136 ersetzt** (121 in den Admin-Vorlagen, 15 in der
Beamer-Ansicht). **135 stehen noch** – die größten Posten:
`phone.html` (22), die Druckvorlagen `schedule_print` (17),
`cabin_signs` (14) und `receipt_print` (6) sowie die beiden
Statistikseiten (19). Die Druckvorlagen gehören zum Punkt
„Druckansichten", der an diesem Tag nicht mehr drankam.

**Nicht verwendet:** SF Symbols oder andere Apple-Symbole.

---

## Farben

Die zehn Themes sind **selbst entworfen**, nicht aus einer fremden Palette
übernommen. Als Orientierung für Helligkeitsabstufungen dienten die
Prinzipien offener Farbsysteme (Radix Colors, Open Props) – übernommen
wurden keine Farbwerte, sondern nur die Idee abgestufter Skalen.

Jede Variante ist gegen WCAG 2.1 AA geprüft:

| Kombination | Mindestkontrast |
|---|---|
| Fließtext auf Fläche | 4,5 : 1 |
| Nebentext auf Fläche | 4,5 : 1 |
| Text auf Akzentfläche (Knopf) | 4,5 : 1 |
| Große Schrift, Hinweistext | 3,0 : 1 |
| Akzent als Rahmen oder Symbol | 3,0 : 1 |
| Rahmen von Eingabefeldern | 3,0 : 1 (WCAG 1.4.11) |

Nachrechnen mit:

```
python3 scripts/kontrast_pruefen.py
```

Das Skript liest `app/static/css/tokens.css`, löst Verweise auf und gibt
für jede der 20 Varianten den schlechtesten Wert aus. Rückgabewert 1,
wenn eine Pflichtkombination durchfällt – damit lässt es sich in eine
Prüfkette hängen.

---

## Bibliotheken (schon vorher im Projekt, jetzt lokal)

| Name | Version | Lizenz | Zweck |
|---|---|---|---|
| Tabler CSS/JS | 1.0.0-beta21 | MIT | Grundraster im Adminbereich |
| Socket.IO Client | 4.7.5 | MIT | Live-Aktualisierung |
| SortableJS | 1.15.6 | MIT | Reihenfolge per Ziehen |

Diese lagen vorher auf fremden Servern und wurden in der Nachtschicht vom
23./24.10. lokal abgelegt. SortableJS war dabei in **drei verschiedenen
Versionen** eingebunden.

---

## Was bewusst nicht übernommen wurde

Der Auftrag nennt Apple Keynote als Vorbild für die **Bedienlogik**.
Übernommen sind deshalb Prinzipien:

- Leinwand und Inspektor statt verstreuter Einstellungsseiten
- direkte Bearbeitung statt Bearbeitungsmodus
- eine klare Hauptaktion je Ansicht
- Theme-Galerie mit großen Vorschauen statt Farbkästchen
- Vollbild-Präsentation

**Nicht übernommen:** keine Apple-Schriften, keine Apple-Symbole, keine
Keynote-Grafiken, keine Apple-Marken oder -Namen in der Oberfläche.
