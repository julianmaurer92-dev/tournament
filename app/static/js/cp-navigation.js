/* ============================================================
   CupPlan – Navigation (Handy-Schublade)
   ============================================================ */

(function () {
    'use strict';

    const leiste = document.getElementById('nav-leiste');
    const knopf = document.getElementById('nav-auf');
    if (!leiste || !knopf) return;

    let schatten = document.querySelector('.nav-schatten');
    if (!schatten) {
        schatten = document.createElement('div');
        schatten.className = 'nav-schatten';
        document.body.appendChild(schatten);
    }

    function oeffnen() {
        leiste.setAttribute('data-offen', '');
        schatten.setAttribute('data-offen', '');
        knopf.setAttribute('aria-expanded', 'true');
        const erstes = leiste.querySelector('a, button, select');
        if (erstes) erstes.focus();
    }
    function schliessen() {
        leiste.removeAttribute('data-offen');
        schatten.removeAttribute('data-offen');
        knopf.setAttribute('aria-expanded', 'false');
    }
    function umschalten() {
        leiste.hasAttribute('data-offen') ? schliessen() : oeffnen();
    }

    knopf.addEventListener('click', umschalten);
    schatten.addEventListener('click', schliessen);
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && leiste.hasAttribute('data-offen')) {
            schliessen();
            knopf.focus();
        }
    });

    // Beim Wechsel auf breite Bildschirme offene Schublade aufraeumen,
    // sonst bleibt der Schatten liegen.
    window.matchMedia('(min-width: 861px)').addEventListener('change', function (e) {
        if (e.matches) schliessen();
    });
})();
