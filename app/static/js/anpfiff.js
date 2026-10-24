/* ============================================================
   ANPFIFF – Grundverhalten
   ------------------------------------------------------------
   Meldungen, Rückgängig, Speichern, Schubladen, Navigation.
   Bewusst ohne Bibliothek: Die App läuft am Sportplatz im
   Mobilfunknetz, jedes Kilobyte zählt.
   ============================================================ */

(function () {
    'use strict';

    const ap = window.ap = window.ap || {};

    /* ── Meldungen ─────────────────────────────────────────
       Statt eines Dialogs, der die Seite anhält: eine Meldung
       unten, die von selbst verschwindet – mit der Möglichkeit,
       die Aktion zurückzunehmen. */

    ap.meldung = function (text, einstellungen) {
        einstellungen = einstellungen || {};
        const behaelter = document.getElementById('ap-meldungen');
        if (!behaelter) return;

        const el = document.createElement('div');
        el.className = 'ap-meldung' + (einstellungen.fehler ? ' ap-meldung--fehler' : '');

        const inhalt = document.createElement('span');
        inhalt.className = 'ap-meldung-text';
        inhalt.textContent = text;
        el.appendChild(inhalt);

        if (einstellungen.rueckgaengig) {
            const knopf = document.createElement('button');
            knopf.type = 'button';
            knopf.className = 'ap-knopf ap-knopf--klein';
            knopf.textContent = 'Rückgängig';
            knopf.addEventListener('click', function () {
                einstellungen.rueckgaengig();
                el.remove();
            });
            el.appendChild(knopf);
        }

        behaelter.appendChild(el);
        setTimeout(function () { el.remove(); },
                   einstellungen.dauer || (einstellungen.rueckgaengig ? 6000 : 3500));
        return el;
    };

    /* ── Rückgängig ────────────────────────────────────────
       Eine Aktion zurücknehmen können ist besser als vorher zu
       fragen. Am Spielfeldrand hält ein Bestätigungsdialog die
       ganze Seite an – auch die Live-Aktualisierung. */

    let letzteAktion = null;

    ap.merken = function (beschreibung, zuruecknehmen) {
        letzteAktion = { beschreibung: beschreibung, zuruecknehmen: zuruecknehmen };
    };

    ap.rueckgaengig = function () {
        if (!letzteAktion) return;
        const a = letzteAktion;
        letzteAktion = null;
        Promise.resolve(a.zuruecknehmen()).then(function () {
            ap.meldung(a.beschreibung + ' zurückgenommen.');
        });
    };

    document.addEventListener('keydown', function (e) {
        const istZ = e.key === 'z' || e.key === 'Z';
        if (!istZ || !(e.metaKey || e.ctrlKey) || e.shiftKey) return;
        // Im Textfeld gehört Strg+Z dem Textfeld
        const ziel = e.target;
        if (/^(INPUT|TEXTAREA|SELECT)$/.test(ziel.tagName) || ziel.isContentEditable) return;
        if (!letzteAktion) return;
        e.preventDefault();
        ap.rueckgaengig();
    });

    /* ── Speichern ─────────────────────────────────────────
       Fehler werden sichtbar gemacht, nicht in die Konsole
       geschrieben. Wer im Zelt steht, hat keine Konsole offen. */

    ap.speichern = function (url, daten, einstellungen) {
        einstellungen = einstellungen || {};
        return fetch(url, {
            method: einstellungen.methode || 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(daten)
        }).then(function (antwort) {
            return antwort.json().catch(function () { return {}; })
                .then(function (d) {
                    if (!antwort.ok || d.error) {
                        throw new Error(d.error || ('Fehler ' + antwort.status));
                    }
                    return d;
                });
        }).catch(function (fehler) {
            const text = /Failed to fetch|NetworkError/.test(fehler.message)
                ? 'Keine Verbindung. Die Änderung wurde nicht gespeichert.'
                : fehler.message;
            ap.meldung(text, { fehler: true, dauer: 6000 });
            throw fehler;
        });
    };

    /* ── Schublade von unten ───────────────────────────────── */

    ap.schublade = function (titel, inhalt, einstellungen) {
        einstellungen = einstellungen || {};
        const grund = document.createElement('div');
        grund.className = 'ap-schublade-grund';
        grund.setAttribute('data-offen', '');
        grund.innerHTML =
            '<div class="ap-schublade" role="dialog" aria-modal="true">' +
            '<div class="ap-schublade-griff"></div>' +
            '<div class="ap-schublade-kopf"><span class="ap-schublade-titel"></span>' +
            '<button type="button" class="ap-knopf ap-knopf--still ap-knopf--symbol ap-rechts" ' +
            'aria-label="Schließen">✕</button></div>' +
            '<div class="ap-schublade-inhalt"></div></div>';

        grund.querySelector('.ap-schublade-titel').textContent = titel;
        const ziel = grund.querySelector('.ap-schublade-inhalt');
        if (typeof inhalt === 'string') ziel.innerHTML = inhalt;
        else ziel.appendChild(inhalt);

        function zu() {
            grund.remove();
            document.removeEventListener('keydown', beiTaste);
            if (einstellungen.beimSchliessen) einstellungen.beimSchliessen();
        }
        function beiTaste(e) { if (e.key === 'Escape') zu(); }

        grund.addEventListener('click', function (e) { if (e.target === grund) zu(); });
        grund.querySelector('button[aria-label="Schließen"]').addEventListener('click', zu);
        document.addEventListener('keydown', beiTaste);
        document.body.appendChild(grund);

        const ersterKnopf = ziel.querySelector('button, a, input, select');
        if (ersterKnopf) ersterKnopf.focus();
        return { schliessen: zu, element: grund };
    };

    /* ── Navigation auf kleinen Bildschirmen ───────────────── */

    const leiste = document.getElementById('ap-leiste');
    const schatten = document.getElementById('ap-leiste-schatten');

    function leisteAuf(an) {
        if (!leiste) return;
        if (an) {
            leiste.setAttribute('data-offen', '');
            if (schatten) schatten.setAttribute('data-offen', '');
        } else {
            leiste.removeAttribute('data-offen');
            if (schatten) schatten.removeAttribute('data-offen');
        }
        document.querySelectorAll('#ap-auf, #ap-auf-unten').forEach(function (k) {
            k.setAttribute('aria-expanded', an ? 'true' : 'false');
        });
    }

    ['ap-auf', 'ap-auf-unten'].forEach(function (id) {
        const k = document.getElementById(id);
        if (k) k.addEventListener('click', function () {
            leisteAuf(!leiste.hasAttribute('data-offen'));
        });
    });
    if (schatten) schatten.addEventListener('click', function () { leisteAuf(false); });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && leiste && leiste.hasAttribute('data-offen')) leisteAuf(false);
    });
    // Beim Wechsel auf den großen Bildschirm die Schublade vergessen
    window.addEventListener('resize', function () {
        if (window.innerWidth >= 900) leisteAuf(false);
    });

    /* ── Zahlen, die sich ändern, kurz hervorheben ─────────── */

    ap.hervorheben = function (el) {
        if (!el || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        el.animate(
            [{ transform: 'scale(1)' }, { transform: 'scale(1.18)' }, { transform: 'scale(1)' }],
            { duration: 420, easing: 'cubic-bezier(.2,.7,.3,1)' });
    };
})();
