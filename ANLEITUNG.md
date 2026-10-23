# CupPlan – Benutzeranleitung

**Version:** 1.5
**Erstellt:** 15.03.2026
**Autor:** Maurer Julian – Designer & Developer

---

## Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Ansichten im Überblick](#ansichten-im-überblick)
3. [Anwender-Anleitung](#anwender-anleitung)
   - [Live-Ansicht (Desktop)](#live-ansicht-desktop)
   - [Smartphone-Ansicht](#smartphone-ansicht)
   - [TV-Ansicht](#tv-ansicht)
   - [Speisekarte](#speisekarte-anwender)
4. [Admin-Anleitung](#admin-anleitung)
   - [Anmelden](#anmelden)
   - [Turnierliste](#turnierliste)
   - [Turnier erstellen](#turnier-erstellen)
   - [Dashboard](#dashboard)
   - [Gruppen & Teams](#gruppen--teams)
   - [Spielsteuerung](#spielsteuerung)
   - [Finalrunde](#finalrunde)
   - [Turniereinstellungen](#turniereinstellungen)
   - [Speisekarte verwalten](#speisekarte-verwalten)
   - [Kabinenschilder](#kabinenschilder)
   - [Spielplan drucken](#spielplan-drucken)
   - [Organisation & Kasse](#organisation--kasse)
   - [Design & Farben](#design--farben)
   - [Export & Import](#export--import)
   - [Benutzerverwaltung](#benutzerverwaltung)
5. [Rollen & Berechtigungen](#rollen--berechtigungen)
6. [Tipps & Hinweise](#tipps--hinweise)

---

## Übersicht

CupPlan ist eine webbasierte Turnierverwaltung für Sportveranstaltungen (z. B. Fußball-Turnierwochenenden). Sie ermöglicht die Live-Verwaltung von Gruppen, Teams, Spielergebnissen und Finalphasen – mit separaten Ansichten für Smartphone, TV-Bildschirm und Desktop.

---

## Ansichten im Überblick

| URL | Zweck |
|-----|-------|
| `/` | Turnierliste (öffentlich, Desktop) |
| `/t/<turnier>/` | Live-Ansicht eines Turniers (Desktop) |
| `/phone/` | Smartphone-Startseite |
| `/t/<turnier>/phone/` | Smartphone-Ansicht eines Turniers |
| `/t/<turnier>/tv/` | TV-Vollbild-Ansicht |
| `/speisekarte` | Speisekarte (Desktop) |
| `/phone/speisekarte` | Speisekarte (Smartphone) |
| `/admin/` | Adminbereich (Login erforderlich) |

---

## Anwender-Anleitung

### Live-Ansicht (Desktop)

Die Desktop-Ansicht unter `/t/<turnier>/` zeigt das gesamte Turniergeschehen in Echtzeit:

- **Live-Spiel** – Aktuell laufendes Spiel mit Ergebnis und Timer
- **Tabelle** – Gruppenstandings mit Punkten, Tordifferenz und Spielen
- **Vergangene Spiele** – Abgeschlossene Begegnungen mit Endergebnis
- **Nächste Spiele** – Kommende Partien
- **Finalrunde** – Bracket-Ansicht der KO-Phase (sobald aktiv)

> **Hinweis:** Ergebnisse und Tabellen können vom Administrator ausgeblendet werden (z. B. für Spannung vor der Bekanntgabe).

---

### Smartphone-Ansicht

Die Smartphone-Ansicht ist für Mobilgeräte optimiert und über `/phone/` erreichbar.

**Startseite (`/phone/`)**

- Liste aller aktiven Turniere
- Direktlink zur Speisekarte
- Vorschau der Turnierbestimmungen

**Turnier-Detailansicht**

Die Seite ist in vier Tabs unterteilt:

| Tab | Inhalt |
|-----|--------|
| 🔴 **Live** | Aktuell laufendes Spiel mit Timer und Ergebnis |
| 📋 **Spiele** | Vergangene und kommende Spiele |
| 📊 **Tabelle** | Gruppenstandings |
| 📄 **Bestimmungen** | Turnierregeln und Fairplay-Bestimmungen |

> **Tipp:** Beim Antippen von „Turnierbestimmungen" auf der Startseite wird der Tab automatisch geöffnet.

---

### TV-Ansicht

Die TV-Ansicht unter `/t/<turnier>/tv/` ist für große Bildschirme und Beamer optimiert:

- **Linke Spalte** – Gruppentabellen
- **Mitte** – Live-Spiel mit großem Timer und Ergebnis, darunter das nächste Spiel
- **Rechte Spalte** – Wechsel zwischen laufenden Spielen und Spielplan (Tabs oben)

Die Ansicht aktualisiert sich automatisch in Echtzeit über eine WebSocket-Verbindung.

---

### Speisekarte (Anwender)

Erreichbar unter `/speisekarte` (Desktop) oder `/phone/speisekarte` (Smartphone).

Zeigt alle eingetragenen Speisen und Getränke mit Name, Beschreibung und Preis.

---

## Admin-Anleitung

### Anmelden

1. Seite `/admin/` aufrufen
2. Benutzername und Passwort eingeben
3. Mit „Anmelden" bestätigen

> Das initiale Admin-Konto wird beim ersten Start automatisch angelegt. Zugangsdaten beim Superadmin erfragen.

---

### Turnierliste

Die Startseite des Adminbereichs zeigt alle Turniere als Kacheln. Von hier aus:

- **Dashboard** öffnen – Verwaltung eines einzelnen Turniers
- **Bearbeiten** – Name, Datum, Spielzeit, Felder und Sichtbarkeitseinstellungen ändern
- **Löschen** – Turnier mit allen Daten unwiderruflich entfernen (nur Superadmin)

---

### Turnier erstellen

Im Erstellungsformular oben auf der Turnierliste:

| Feld | Beschreibung |
|------|-------------|
| **Name** | Anzeigename des Turniers (z. B. „U13 Turnier") |
| **Datum** | Veranstaltungsdatum |
| **Uhrzeit** | Startzeit der Veranstaltung |
| **Beschreibung** | Kurze Beschreibung (optional) |
| **Spielzeit** | Reguläre Spielzeit in Minuten (Standard: 10) |
| **Verlängerung** | Verlängerungszeit in Minuten (Standard: 5) |
| **Spielfelder** | Anzahl gleichzeitig bespielter Felder (1 oder 2) |
| **Finalrundentyp** | Kann vorab oder später festgelegt werden |
| **Ergebnisse ausblenden** | Tabelle und Ergebnisse in allen Ansichten verbergen |

Nach dem Erstellen erscheint das Turnier in der Turnierliste und kann über „Dashboard" verwaltet werden.

---

### Dashboard

Das Dashboard ist die zentrale Verwaltungsseite eines Turniers. Es gliedert sich in folgende Bereiche:

#### Steuerleiste (oben)

- **Phase** – Zeigt die aktuelle Turnierphase (Gruppenphase / Finalrunde / Abgeschlossen)
- **Gruppenphase beenden** – Öffnet die Finalrunden-Auswahl
- **Turnier beenden** – Schließt das Turnier ab (nur in der Finalrunde)
- **Zurücksetzen** – Setzt auf Gruppenphase zurück (löscht alle Finalspiele)

#### Linke Spalte – Tabellen

Zeigt die aktuellen Gruppenstandings in Echtzeit.

#### Mittlere Spalte – Spiele

- **Laufende Spiele** – Aktiv gestartete Spiele
- **Kommende Spiele** – Geplante Spiele mit Drag-and-Drop-Sortierung
- **Abgeschlossene Spiele** – Beendete Spiele

#### Rechte Spalte – Finalvorschau

Sobald eine Finalrunde eingerichtet ist, werden die prognostizierten oder realen Paarungen angezeigt. Diese können per Drag-and-Drop umsortiert und mit dem ⇄-Button (Heim/Gast) getauscht werden.

---

### Gruppen & Teams

Im **Turnier-Admin** (`/admin/t/<turnier>/settings`) unter dem Reiter **Gruppen & Teams**:

#### Gruppen erstellen

1. Gruppenname eingeben (z. B. „Gruppe A")
2. Mit „Hinzufügen" bestätigen
3. Anzeigereihenfolge kann per Drag-and-Drop angepasst werden

#### Teams eintragen

1. Team-Name eingeben
2. Gruppe auswählen (optional: ohne Gruppe)
3. Mit „Hinzufügen" bestätigen

**CSV-Import** – Teams können per CSV-Datei massenimportiert werden:

```
Teamname; Gruppenname
FC Muster; Gruppe A
SV Beispiel; Gruppe B
```

#### Spiele generieren

Nach dem Eintragen aller Teams:

1. Gruppe(n) auswählen
2. „Spiele generieren" klicken → Jeder gegen Jeden innerhalb der Gruppe

---

### Spielsteuerung

Die **Spielsteuerung** (`/admin/t/<turnier>/match-control`) ist das Herzstück der Live-Verwaltung.

#### Spiel starten

1. Geplantes Spiel in der Liste auswählen
2. „Starten" klicken → Spiel wird auf „Live" gesetzt, Timer startet

#### Timer

| Aktion | Beschreibung |
|--------|-------------|
| ▶ Start/Pause | Timer läuft oder wird pausiert |
| ↺ Reset | Timer auf Ausgangswert zurücksetzen |
| +/- | Tore für Heim- oder Gastmannschaft |
| Halbzeit/VL | Wechsel zwischen regulärer Zeit und Verlängerung |

#### Spiel beenden

„Beenden" klickt → Ergebnis wird gespeichert, Tabelle aktualisiert sich automatisch.

> **Hinweis:** Beim Betrieb mit 2 Feldern können zwei Spiele gleichzeitig laufen. Jedes Feld hat eine eigene Steuerungskarte.

---

### Finalrunde

#### Gruppenphase beenden

Im Dashboard auf „Gruppenphase beenden" klicken. Es öffnet sich ein Auswahlfenster mit drei Bereichen:

**1. Neue Finalrunde erstellen**

| Option | Beschreibung |
|--------|-------------|
| HF + Finale | 4 Teams: 2 Halbfinale + Finale + Spiel um Platz 3 |
| Platzierungsspiele | 1.A vs 1.B, 2.A vs 2.B usw. |
| Direktes Finale | Bester vs. Zweitbester |
| Klassisch KO | Automatische Setzliste nach Punkten |
| Freie KO | Manuelle Zusammenstellung |
| Eigene Paarungen | Vollständig freie Eingabe |

**2. Definierte Finalrunde spielen** *(nur sichtbar wenn bereits Finalspiele vorhanden)*

Bereits eingerichtete Finalspiele direkt starten ohne neu zu generieren.

**3. Ohne Finalrunde**

Das Turnier endet nach der Gruppenphase ohne Finalrunde.

#### Finalrunden-Setup

Nach der Auswahl (außer „Ohne Finalrunde") wird zur Setup-Seite weitergeleitet. Dort können:

- Paarungen manuell angepasst werden
- Teams für Slots eingetragen werden
- Die Reihenfolge der Spiele per Drag-and-Drop geändert werden

#### Finalspiele steuern

Genauso wie Gruppenspiele – über die Spielsteuerung. Die Finalpaarungen werden als Bracket dargestellt.

---

### Turniereinstellungen

Unter `/admin/t/<turnier>/settings`:

#### Allgemein

- **Turniername** – Anzeigename in der Live-Ansicht
- **Ankündigung** – Freitext, der oben in der Live-Ansicht erscheint
- **Turnierbestimmungen** – Regeln und Fairplay-Bestimmungen (bis 5.000 Zeichen), erscheinen als eigener Tab in der Smartphone-Ansicht

#### Anzeige

| Einstellung | Beschreibung |
|-------------|-------------|
| Ergebnisse ausblenden | Scores und Tabelle in allen Ansichten verbergen |
| Spielfelder | Anzahl aktiver Spielfelder |
| Timer regulär | Standard-Spielzeit in Sekunden |
| Timer Verlängerung | Standard-Verlängerungszeit |

---

### Speisekarte verwalten

Unter `/admin/menu/`:

#### Eintrag hinzufügen

1. Kategorie wählen: **Speise** oder **Getränk**
2. Name, Preis und optionale Beschreibung eingeben
3. „Hinzufügen" klicken

#### Einträge bearbeiten

- **Bearbeiten-Button** – Inline-Bearbeitungszeile öffnet sich direkt in der Tabelle
- **Löschen-Button** – Einzelnen Eintrag entfernen

#### Reihenfolge ändern

Zeilen per **↕ Drag-Handle** (linke Spalte) verschieben. Die neue Reihenfolge wird sofort gespeichert.

#### Mehrere Einträge löschen

1. Checkboxen links in den Zeilen aktivieren
2. „Auswahl löschen" in der erscheinenden Toolbar klicken
3. Bestätigen

#### CSV-Import

1. „CSV importieren" klicken
2. CSV-Text einfügen oder Datei laden
3. Format: `Name; Preis; Beschreibung; Kategorie`

```
Bratwurst; 3,50 €; mit Senf; speise
Cola; 2,00 €; 0,33l; getraenk
```

---

### Kabinenschilder

Unter `/admin/t/<turnier>/cabin-signs`:

Kabinenschilder können für den Druck vorbereitet werden:

- Teams per **Drag-and-Drop** zwischen Kabinen verschieben
- **+ Button** – Team einer weiteren Kabine als Alternative zuweisen (erscheint mit amber Markierung)
- **Teamnamen** direkt in der Ansicht bearbeiten (klicken und tippen)
- Teams aus einer Kabine mit **✕** entfernen
- **Drucken** – Druckansicht öffnen (Steuerelemente werden ausgeblendet)

---

### Spielplan drucken

Unter `/admin/t/<turnier>/schedule-print`:

- Wahl zwischen **aktuellem Stand** (mit Ergebnissen) und **leerem Spielplan** (für Aushang vor dem Turnier)
- Druckoptimierte Darstellung aller Gruppenspiele und Finalspiele

---

### Organisation & Kasse

Unter `/admin/t/<turnier>/organisation`:

- **Startgebühren** verwalten – Bezahlstatus pro Team erfassen
- **Quittungen** drucken – Pro Team eine Quittung generieren
- Übersicht über gezahlte und ausstehende Beträge

---

### Design & Farben

Unter `/admin/t/<turnier>/design`:

| Einstellung | Beschreibung |
|-------------|-------------|
| Primärfarbe | Akzentfarbe (Buttons, Highlights) – Standard: Grün |
| Titelfarbe | Farbe des Turniernamens |
| Sekundärfarbe | Hintergrundfarbe der Karten |
| Thema | Dark / Light |
| Logo-URL | URL zum Vereinslogo |
| Ergebnisse ausblenden | Scores und Tabelle ausblenden |

Änderungen werden sofort in der Live-Ansicht übernommen.

---

### Export & Import

Unter `/admin/export-import/`:

#### Exportieren

1. Gewünschte Turniere per Checkbox auswählen
2. Optional: „Speisen & Getränke einschließen" aktivieren
3. „Exportieren" klicken → JSON-Datei wird heruntergeladen

Die Datei enthält alle Turnierdaten: Gruppen, Teams, Spiele, Einstellungen und optional die Speisekarte.

#### Importieren

1. „Datei auswählen" klicken und JSON-Backup laden
2. Aus der Liste der enthaltenen Turniere auswählen
3. Optional: „Speisekarten-Einträge importieren" aktivieren
4. „Importieren" klicken

> **Hinweis:** Bereits vorhandene Turniernamen werden mit einem Suffix versehen, bestehende Daten werden nicht überschrieben. Bei der Speisekarte werden Duplikate (gleicher Name) übersprungen.

---

### Benutzerverwaltung

Unter `/admin/users/` *(nur Superadmin)*:

#### Benutzer erstellen

1. Benutzername und Passwort eingeben
2. Rolle auswählen (siehe [Rollen & Berechtigungen](#rollen--berechtigungen))
3. Turnierzuweisungen setzen (nicht relevant für Superadmin)
4. „Erstellen" klicken

#### Benutzer bearbeiten

- Passwort ändern, Rolle anpassen, Turnierzuweisungen aktualisieren

#### Benutzer löschen

- Eigenes Konto kann nicht gelöscht werden

---

## Rollen & Berechtigungen

| Funktion | Superadmin | Editor | Viewer |
|----------|-----------|--------|--------|
| Turniere erstellen/löschen | ✅ | ❌ | ❌ |
| Turniere bearbeiten | ✅ | ✅* | ❌ |
| Gruppen & Teams verwalten | ✅ | ✅* | ❌ |
| Spielsteuerung (Live) | ✅ | ✅* | ❌ |
| Einstellungen ändern | ✅ | ✅* | ❌ |
| Dashboard lesen | ✅ | ✅* | ✅* |
| Speisekarte verwalten | ✅ | ❌ | ❌ |
| Export & Import | ✅ | ❌ | ❌ |
| Benutzerverwaltung | ✅ | ❌ | ❌ |

*\* Nur für zugewiesene Turniere*

---

## Tipps & Hinweise

### Echtzeit-Updates

Alle Live-Ansichten (Phone, TV, Desktop) aktualisieren sich automatisch über WebSockets. Es ist kein manuelles Neuladen nötig.

### Ergebnisse ausblenden

Die Option „Ergebnisse & Tabelle ausblenden" sorgt dafür, dass in **allen** Ansichten (Desktop, Smartphone, TV) weder Ergebnisse noch Tabellen sichtbar sind. Das eignet sich z. B. um die Spannung aufrechtzuerhalten bis zur offiziellen Bekanntgabe.

### Backup vor dem Turnier

Vor Beginn einer Veranstaltung empfiehlt sich ein Export-Backup unter `/admin/export-import/`. So können alle Turnierdaten und die Speisekarte gesichert und bei Bedarf wiederhergestellt werden.

### QR-Codes für Teilnehmer

Die Smartphone-Ansicht (`/phone/`) kann als QR-Code auf Aushängen bereitgestellt werden, damit Teilnehmer das Turnier live verfolgen können.

### TV-Bildschirm einrichten

Den Browser auf dem TV-Gerät in den Vollbildmodus versetzen (F11) und die URL `/t/<turnier>/tv/` aufrufen. Die Ansicht benötigt keine Bedienung und aktualisiert sich automatisch.

### Zwei Spielfelder

Bei Aktivierung von „2 Felder" in den Turniereinstellungen können zwei Spiele gleichzeitig live sein. In der Spielsteuerung erscheinen beide Felder als separate Karten.
