/* ============================================================
   ANPFIFF – Theme-Galerie
   ------------------------------------------------------------
   Ein Klick wendet an. Die Vorschau passiert direkt am
   <html>-Element dieser Seite: data-theme umsetzen, und die
   ganze Oberfläche wechselt mit. Man sieht sofort, worauf man
   sich einlässt – nicht erst nach dem Speichern in einem
   anderen Tab.
   ============================================================ */

(function () {
    'use strict';

    const galerie = document.getElementById('ga-galerie');
    if (!galerie) return;

    const wurzel = document.documentElement;
    const karten = Array.from(galerie.querySelectorAll('.ga-karte'));
    const schemaKnoepfe = Array.from(document.querySelectorAll('[data-schema]'));

    function wert() { return AKTUELLES_THEME + ':' + AKTUELLES_SCHEMA; }

    function anzeigen() {
        wurzel.dataset.theme = AKTUELLES_THEME;
        wurzel.dataset.schema = AKTUELLES_SCHEMA;
        // Tabler braucht seinen eigenen Schalter für hell/dunkel
        wurzel.dataset.bsTheme = AKTUELLES_SCHEMA === 'hell' ? 'light' : 'dark';

        karten.forEach(function (karte) {
            const gewaehlt = karte.dataset.theme === AKTUELLES_THEME;
            karte.classList.toggle('ist-gewaehlt', gewaehlt);
            karte.setAttribute('aria-checked', gewaehlt ? 'true' : 'false');

            const v = karte.querySelector('.ga-vorschau');
            const farben = JSON.parse(karte.dataset[AKTUELLES_SCHEMA] || '[]');
            if (v && farben.length === 3) {
                v.style.setProperty('--v-grund', farben[0]);
                v.style.setProperty('--v-tafel', farben[1]);
                v.style.setProperty('--v-akzent', farben[2]);
            }
        });

        schemaKnoepfe.forEach(function (k) {
            k.setAttribute('aria-pressed',
                k.dataset.schema === AKTUELLES_SCHEMA ? 'true' : 'false');
            // "Anzeigetafel" hat keine helle Variante.
            k.disabled = NUR_DUNKEL.indexOf(AKTUELLES_THEME) >= 0 && k.dataset.schema === 'hell';
        });
    }

    function sichern(text, vorherT, vorherS) {
        return ap.speichern('/admin/t/' + SLUG + '/api/settings', { theme: wert() })
            .then(function () {
                ap.merken(text, function () {
                    AKTUELLES_THEME = vorherT;
                    AKTUELLES_SCHEMA = vorherS;
                    anzeigen();
                    return ap.speichern('/admin/t/' + SLUG + '/api/settings',
                                        { theme: wert() });
                });
                ap.meldung(text, { rueckgaengig: ap.rueckgaengig });
            })
            .catch(function () {
                // Fehlgeschlagen: zurück auf den Stand, der wirklich gilt
                AKTUELLES_THEME = vorherT;
                AKTUELLES_SCHEMA = vorherS;
                anzeigen();
            });
    }

    karten.forEach(function (karte) {
        karte.addEventListener('click', function () {
            if (karte.dataset.theme === AKTUELLES_THEME) return;
            const vT = AKTUELLES_THEME, vS = AKTUELLES_SCHEMA;
            AKTUELLES_THEME = karte.dataset.theme;
            if (NUR_DUNKEL.indexOf(AKTUELLES_THEME) >= 0) AKTUELLES_SCHEMA = 'dunkel';
            anzeigen();   // sofort sichtbar, bevor der Server antwortet
            sichern('Theme „' + karte.querySelector('.ga-name').textContent.trim() +
                    '" übernommen.', vT, vS);
        });
    });

    schemaKnoepfe.forEach(function (k) {
        k.addEventListener('click', function () {
            if (k.dataset.schema === AKTUELLES_SCHEMA) return;
            const vT = AKTUELLES_THEME, vS = AKTUELLES_SCHEMA;
            AKTUELLES_SCHEMA = k.dataset.schema;
            anzeigen();
            sichern(AKTUELLES_SCHEMA === 'hell' ? 'Helle Variante.' : 'Dunkle Variante.',
                    vT, vS);
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

    const wahl = document.getElementById('ga-farbwahl');
    const text = document.getElementById('ga-farbtext');
    const hinweis = document.getElementById('ga-farbhinweis');
    const weg = document.getElementById('ga-farbweg');

    function farbeSpeichern(w) {
        if (!/^#[0-9a-fA-F]{6}$/.test(w)) {
            hinweis.textContent = 'Bitte eine Farbe wie #11703f angeben.';
            return;
        }
        hinweis.textContent = '';
        ap.speichern('/admin/t/' + SLUG + '/api/settings', { color_primary: w })
            .then(function () {
                ap.meldung('Vereinsfarbe übernommen. Lade die Seite neu, um sie überall zu sehen.',
                           { dauer: 5000 });
            });
    }

    if (wahl) {
        wahl.addEventListener('change', function () {
            text.value = wahl.value; farbeSpeichern(wahl.value);
        });
        text.addEventListener('change', function () {
            const w = text.value.trim();
            if (/^#[0-9a-fA-F]{6}$/.test(w)) wahl.value = w;
            farbeSpeichern(w);
        });
        weg.addEventListener('click', function () {
            // Die Akzentfarbe des Themes wieder gelten lassen: dafür
            // setzen wir die Vereinsfarbe auf genau diesen Wert.
            const karte = galerie.querySelector('.ga-karte.ist-gewaehlt');
            if (!karte) return;
            const farben = JSON.parse(karte.dataset[AKTUELLES_SCHEMA] || '[]');
            if (farben.length === 3) {
                wahl.value = farben[2]; text.value = farben[2];
                farbeSpeichern(farben[2]);
            }
        });
    }

    anzeigen();
})();
