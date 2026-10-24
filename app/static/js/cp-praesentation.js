/* ============================================================
   CupPlan – Beamer-Praesentation
   ------------------------------------------------------------
   Hinstellen, einmal starten, laufen lassen.

   Baut auf der Umschaltung auf, die die Beamer-Ansicht fuer kleine
   Bildschirme schon hat (showTab). Neu ist, dass sie unabhaengig von
   der Fensterbreite gilt und von selbst weiterblaettert.
   ============================================================ */

(function () {
    'use strict';

    const SEITEN = [
        { schluessel: 'live',    name: 'Live',          dauer: 20000 },
        { schluessel: 'table',   name: 'Tabellen',      dauer: 15000 },
        { schluessel: 'matches', name: 'Spielplan',     dauer: 15000 },
    ];

    let laeuft = false;
    let i = 0;
    let pausiert = false;
    let beginn = 0;
    let takt = null;

    const koerper = document.body;
    const leiste = {
        name: document.getElementById('pr-seitenname'),
        punkte: document.getElementById('pr-punkte'),
        balken: document.getElementById('pr-balken'),
        pause: document.getElementById('pr-pause'),
    };
    const hilfe = document.getElementById('pr-hilfe');
    const willkommen = document.getElementById('pr-willkommen');

    /* Manche Browser verweigern Vollbild ohne Nutzeraktion. Das ist
       kein Fehler, den jemand sehen muss – die Praesentation laeuft
       auch im Fenster. */
    function vollbild(an) {
        try {
            if (an && !document.fullscreenElement) {
                const v = document.documentElement.requestFullscreen();
                if (v && v.catch) v.catch(function () {});
            } else if (!an && document.fullscreenElement) {
                document.exitFullscreen();
            }
        } catch (e) { /* dann eben im Fenster */ }
    }

    function punkteBauen() {
        leiste.punkte.innerHTML = '';
        SEITEN.forEach(function (_, n) {
            const p = document.createElement('span');
            p.className = 'pr-punkt' + (n === i ? ' ist-aktiv' : '');
            leiste.punkte.appendChild(p);
        });
    }

    function zeigen(n) {
        i = (n + SEITEN.length) % SEITEN.length;
        const seite = SEITEN[i];
        showTab(seite.schluessel);
        leiste.name.textContent = seite.name;
        punkteBauen();
        beginn = Date.now();
        leiste.balken.style.width = '0%';
    }

    function weiter(schritt) {
        zeigen(i + schritt);
    }

    function ticken() {
        if (!laeuft) return;
        if (pausiert) { beginn = Date.now(); return; }
        const anteil = (Date.now() - beginn) / SEITEN[i].dauer;
        leiste.balken.style.width = Math.min(100, anteil * 100) + '%';
        if (anteil >= 1) weiter(1);
    }

    function starten(mitVollbild) {
        if (laeuft) return;
        laeuft = true;
        koerper.dataset.praesentation = '';
        if (mitVollbild) vollbild(true);
        zeigen(0);
        clearInterval(takt);
        takt = setInterval(ticken, 200);
        hilfeZeigen();
    }

    function beenden() {
        if (!laeuft) return;
        laeuft = false;
        pausiert = false;
        clearInterval(takt);
        delete koerper.dataset.praesentation;
        vollbild(false);
        // Zurueck auf die drei Spalten
        document.querySelectorAll('.tab-col').forEach(function (el) {
            el.classList.remove('tab-active');
        });
        document.getElementById('col-live').style.display = 'flex';
    }

    function pause(an) {
        pausiert = an;
        leiste.pause.textContent = an ? 'Angehalten' : '';
        if (!an) beginn = Date.now();
    }

    /* ── Tastenhilfe: zeigt sich bei Bewegung, verschwindet wieder ── */

    let hilfeUhr = null;
    function hilfeZeigen() {
        if (!laeuft) return;
        hilfe.setAttribute('data-sichtbar', '');
        clearTimeout(hilfeUhr);
        hilfeUhr = setTimeout(function () {
            hilfe.removeAttribute('data-sichtbar');
        }, 3000);
    }
    document.addEventListener('mousemove', hilfeZeigen);

    /* ── Tastatur ──────────────────────────────────────────── */

    document.addEventListener('keydown', function (e) {
        if (willkommen && willkommen.hasAttribute('data-offen')) {
            e.preventDefault();
            losgehen();
            return;
        }
        if (!laeuft) {
            if (e.key === 'p' || e.key === 'P') starten(true);
            return;
        }
        switch (e.key) {
            case 'ArrowRight': case 'PageDown':
                e.preventDefault(); weiter(1); hilfeZeigen(); break;
            case 'ArrowLeft': case 'PageUp':
                e.preventDefault(); weiter(-1); hilfeZeigen(); break;
            case ' ':
                e.preventDefault(); pause(!pausiert); hilfeZeigen(); break;
            case 'Escape':
                beenden(); break;
            case '1': case '2': case '3':
                zeigen(parseInt(e.key, 10) - 1); hilfeZeigen(); break;
        }
    });

    /* Verlaesst jemand das Vollbild ueber F11 oder die Browserleiste,
       soll die Praesentation nicht als halbe Sache weiterlaufen. */
    document.addEventListener('fullscreenchange', function () {
        if (!document.fullscreenElement && laeuft) beenden();
    });

    /* ── Start ─────────────────────────────────────────────── */

    function losgehen() {
        if (willkommen) willkommen.removeAttribute('data-offen');
        starten(true);
    }

    const knopf = document.getElementById('pr-start');
    if (knopf) knopf.addEventListener('click', function () { starten(true); });

    if (willkommen) {
        willkommen.addEventListener('click', losgehen);
        if (new URLSearchParams(location.search).get('praesentieren') === '1') {
            willkommen.setAttribute('data-offen', '');
        }
    }

    window.cpPraesentation = { starten: starten, beenden: beenden, weiter: weiter,
                               pause: pause, laeuft: function () { return laeuft; } };
})();
