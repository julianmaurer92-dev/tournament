/* ============================================================
   CupPlan – Theme-Galerie
   ------------------------------------------------------------
   Ein Klick wendet an. Kein Speichern-Knopf, kein Zwischenschritt.

   Die Vorschau passiert direkt am <html>-Element dieser Seite:
   data-theme und data-schema umsetzen, und die ganze Oberflaeche
   wechselt mit – man sieht sofort, worauf man sich einlaesst.
   ============================================================ */

(function () {
    'use strict';

    const galerie = document.getElementById('ga-galerie');
    if (!galerie) return;

    const wurzel = document.documentElement;
    const karten = Array.from(galerie.querySelectorAll('.ga-karte'));
    const schemaKnoepfe = Array.from(document.querySelectorAll('.ga-schema-knopf'));

    function speicherwert() { return AKTUELLES_THEME + ':' + AKTUELLES_SCHEMA; }

    function anzeigen() {
        wurzel.dataset.theme = AKTUELLES_THEME;
        wurzel.dataset.schema = AKTUELLES_SCHEMA;
        // Tabler braucht seinen eigenen Schalter fuer hell/dunkel
        wurzel.dataset.bsTheme = AKTUELLES_SCHEMA === 'hell' ? 'light' : 'dark';

        karten.forEach(function (karte) {
            const gewaehlt = karte.dataset.theme === AKTUELLES_THEME;
            karte.classList.toggle('ist-gewaehlt', gewaehlt);
            karte.setAttribute('aria-checked', gewaehlt ? 'true' : 'false');

            // Die Miniatur zeigt das Theme im aktuell gewaehlten Schema
            const farben = JSON.parse(karte.dataset[AKTUELLES_SCHEMA] || '[]');
            const vorschau = karte.querySelector('.ga-vorschau');
            if (vorschau && farben.length === 3) {
                vorschau.style.setProperty('--v-tief', farben[0]);
                vorschau.style.setProperty('--v-flaeche', farben[1]);
                vorschau.style.setProperty('--v-akzent', farben[2]);
            }
        });

        schemaKnoepfe.forEach(function (knopf) {
            knopf.setAttribute('aria-pressed',
                knopf.dataset.schema === AKTUELLES_SCHEMA ? 'true' : 'false');
        });
    }

    function sichern(beschreibung, vorherTheme, vorherSchema) {
        return cp.speichern('/admin/t/' + SLUG + '/api/settings',
                            { theme: speicherwert() })
            .then(function () {
                cp.merken(beschreibung, function () {
                    AKTUELLES_THEME = vorherTheme;
                    AKTUELLES_SCHEMA = vorherSchema;
                    anzeigen();
                    return cp.speichern('/admin/t/' + SLUG + '/api/settings',
                                        { theme: speicherwert() });
                });
                cp.toast(beschreibung, { rueckgaengig: cp.rueckgaengig, dauer: 4000 });
            })
            .catch(function () {
                // Fehlgeschlagen: zurueck auf den Stand, der wirklich gilt
                AKTUELLES_THEME = vorherTheme;
                AKTUELLES_SCHEMA = vorherSchema;
                anzeigen();
            });
    }

    karten.forEach(function (karte) {
        karte.addEventListener('click', function () {
            if (karte.dataset.theme === AKTUELLES_THEME) return;
            const vorherT = AKTUELLES_THEME, vorherS = AKTUELLES_SCHEMA;
            AKTUELLES_THEME = karte.dataset.theme;
            anzeigen();        // sofort sichtbar, bevor der Server antwortet
            const name = karte.querySelector('.ga-karte-name').textContent.trim();
            sichern('Theme „' + name + '" übernommen.', vorherT, vorherS);
        });
    });

    schemaKnoepfe.forEach(function (knopf) {
        knopf.addEventListener('click', function () {
            if (knopf.dataset.schema === AKTUELLES_SCHEMA) return;
            const vorherT = AKTUELLES_THEME, vorherS = AKTUELLES_SCHEMA;
            AKTUELLES_SCHEMA = knopf.dataset.schema;
            anzeigen();
            sichern(AKTUELLES_SCHEMA === 'hell' ? 'Helle Variante.' : 'Dunkle Variante.',
                    vorherT, vorherS);
        });
    });

    // Tastatur: Pfeiltasten durch die Galerie
    galerie.addEventListener('keydown', function (e) {
        if (!/^Arrow(Left|Right|Up|Down)$/.test(e.key)) return;
        const i = karten.indexOf(document.activeElement);
        if (i < 0) return;
        e.preventDefault();
        const vor = e.key === 'ArrowRight' || e.key === 'ArrowDown';
        const ziel = karten[(i + (vor ? 1 : -1) + karten.length) % karten.length];
        ziel.focus();
        ziel.click();
    });

    // ── Vereinsfarbe ───────────────────────────────────────

    const farbWahl = document.getElementById('ga-farbe-wahl');
    const farbText = document.getElementById('ga-farbe-text');
    const farbHinweis = document.getElementById('ga-farbe-hinweis');
    const farbWeg = document.getElementById('ga-farbe-weg');

    function farbeSpeichern(wert) {
        if (!/^#[0-9a-fA-F]{6}$/.test(wert)) {
            farbHinweis.textContent = 'Bitte eine Farbe wie #22c55e angeben.';
            return;
        }
        farbHinweis.textContent = '';
        cp.speichern('/admin/t/' + SLUG + '/api/settings', { color_primary: wert })
            .then(function () {
                cp.toast('Vereinsfarbe übernommen. Lade die Seite neu, um sie überall zu sehen.',
                         { dauer: 4000 });
            });
    }

    if (farbWahl) {
        farbWahl.addEventListener('change', function () {
            farbText.value = farbWahl.value;
            farbeSpeichern(farbWahl.value);
        });
        farbText.addEventListener('change', function () {
            const wert = farbText.value.trim();
            if (/^#[0-9a-fA-F]{6}$/.test(wert)) farbWahl.value = wert;
            farbeSpeichern(wert);
        });
        farbWeg.addEventListener('click', function () {
            // Die Akzentfarbe des Themes wieder gelten lassen: dafuer
            // setzen wir die Vereinsfarbe auf genau diesen Wert.
            const farben = JSON.parse(
                galerie.querySelector('.ga-karte.ist-gewaehlt')
                       .dataset[AKTUELLES_SCHEMA] || '[]');
            if (farben.length === 3) {
                farbWahl.value = farben[2];
                farbText.value = farben[2];
                farbeSpeichern(farben[2]);
            }
        });
    }

    // ── Anzeige-Schalter ───────────────────────────────────

    document.querySelectorAll('[data-einstellung]').forEach(function (feld) {
        feld.addEventListener('change', function () {
            const daten = {};
            daten[feld.dataset.einstellung] = feld.checked ? '1' : '0';
            cp.speichern('/admin/t/' + SLUG + '/api/settings', daten)
                .then(function () {
                    cp.merken('Anzeige geändert', function () {
                        feld.checked = !feld.checked;
                        const zurueck = {};
                        zurueck[feld.dataset.einstellung] = feld.checked ? '1' : '0';
                        return cp.speichern('/admin/t/' + SLUG + '/api/settings', zurueck);
                    });
                    cp.toast('Gespeichert.', { rueckgaengig: cp.rueckgaengig });
                })
                .catch(function () { feld.checked = !feld.checked; });
        });
    });

    anzeigen();
})();
