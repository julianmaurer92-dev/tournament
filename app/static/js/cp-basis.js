/* ============================================================
   CupPlan – Basis-Verhalten
   ------------------------------------------------------------
   Kleine, gemeinsame Bausteine fuer alle Seiten:
     cp.toast()      dezente Bestaetigung, optional mit Rueckgaengig
     cp.rueckgaengig Verlauf + Strg/Cmd+Z
     cp.speichern()  Anfrage mit Fehleranzeige statt stillem Scheitern
     cp.sheet()      Bottom-Sheet auf dem Handy
   Kein Framework, keine Abhaengigkeit.
   ============================================================ */

(function () {
    'use strict';

    const cp = window.cp = window.cp || {};

    // ── Toast ───────────────────────────────────────────────
    // Dezente Rueckmeldung statt blockierendem alert(). Ein Dialog, der
    // die Seite anhaelt, ist am Spielfeldrand das Letzte, was man will.

    cp.toast = function (text, optionen) {
        optionen = optionen || {};
        const behaelter = document.getElementById('cp-toasts');
        if (!behaelter) { console.log('[cp]', text); return; }

        const el = document.createElement('div');
        el.className = 'cp-toast' + (optionen.art === 'gefahr' ? ' cp-toast--gefahr' : '');

        const span = document.createElement('span');
        span.textContent = text;
        span.style.flex = '1';
        el.appendChild(span);

        if (optionen.rueckgaengig) {
            const knopf = document.createElement('button');
            knopf.type = 'button';
            knopf.className = 'cp-knopf cp-knopf--still';
            knopf.textContent = 'Rückgängig';
            knopf.addEventListener('click', function () {
                optionen.rueckgaengig();
                entfernen();
            });
            el.appendChild(knopf);
        }

        behaelter.appendChild(el);
        let zeitgeber = setTimeout(entfernen, optionen.dauer || 5000);

        function entfernen() {
            clearTimeout(zeitgeber);
            el.style.opacity = '0';
            el.style.transform = 'translateY(8px)';
            setTimeout(function () { el.remove(); }, 200);
        }
        el.addEventListener('mouseenter', function () { clearTimeout(zeitgeber); });
        el.addEventListener('mouseleave', function () {
            zeitgeber = setTimeout(entfernen, 2000);
        });
        return entfernen;
    };

    // ── Rueckgaengig ────────────────────────────────────────
    // Statt "Wirklich loeschen?" vor jeder Aktion: erst machen, dann
    // zurueckrollen lassen. Das ist schneller und verzeiht mehr.

    const verlauf = [];

    cp.merken = function (beschreibung, zuruecknehmen) {
        verlauf.push({ beschreibung: beschreibung, zuruecknehmen: zuruecknehmen });
        if (verlauf.length > 25) verlauf.shift();
    };

    cp.rueckgaengig = function () {
        const letzter = verlauf.pop();
        if (!letzter) {
            cp.toast('Nichts zum Rückgängigmachen.');
            return false;
        }
        Promise.resolve(letzter.zuruecknehmen()).then(function () {
            cp.toast(letzter.beschreibung + ' rückgängig gemacht.');
        }).catch(function () {
            cp.toast('Rückgängig hat nicht geklappt.', { art: 'gefahr' });
        });
        return true;
    };

    document.addEventListener('keydown', function (e) {
        const istZ = e.key === 'z' || e.key === 'Z';
        if (!istZ || !(e.metaKey || e.ctrlKey) || e.shiftKey) return;
        const ziel = e.target;
        // In Eingabefeldern gehoert Strg+Z dem Browser
        if (ziel && /^(INPUT|TEXTAREA)$/.test(ziel.tagName)) return;
        if (ziel && ziel.isContentEditable) return;
        if (verlauf.length) { e.preventDefault(); cp.rueckgaengig(); }
    });

    // ── Speichern ───────────────────────────────────────────
    // Eine Anfrage, die Fehler sichtbar macht. Vorher sind Fehler
    // haeufig nur in der Browserkonsole gelandet.

    cp.speichern = function (url, daten, optionen) {
        optionen = optionen || {};
        return fetch(url, {
            method: optionen.methode || 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: daten === undefined ? '{}' : JSON.stringify(daten)
        }).then(function (antwort) {
            return antwort.json().catch(function () { return {}; }).then(function (inhalt) {
                if (!antwort.ok || inhalt.error) {
                    throw new Error(inhalt.error || ('Fehler ' + antwort.status));
                }
                return inhalt;
            });
        }).catch(function (fehler) {
            const text = fehler && fehler.message === 'Failed to fetch'
                ? 'Keine Verbindung. Die Änderung wurde nicht gespeichert.'
                : (fehler.message || 'Unbekannter Fehler');
            cp.toast(text, { art: 'gefahr', dauer: 8000 });
            throw fehler;
        });
    };

    // ── Sheet (Handy) ───────────────────────────────────────

    cp.sheet = function (element) {
        if (!element) return null;
        let hintergrund = element.previousElementSibling;
        if (!hintergrund || !hintergrund.classList.contains('cp-sheet-hintergrund')) {
            hintergrund = document.createElement('div');
            hintergrund.className = 'cp-sheet-hintergrund';
            element.parentNode.insertBefore(hintergrund, element);
        }
        let zuletztFokussiert = null;

        function oeffnen() {
            zuletztFokussiert = document.activeElement;
            hintergrund.setAttribute('data-offen', '');
            element.setAttribute('data-offen', '');
            element.setAttribute('aria-hidden', 'false');
            const erstes = element.querySelector(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (erstes) erstes.focus();
            document.addEventListener('keydown', aufEscape);
        }
        function schliessen() {
            hintergrund.removeAttribute('data-offen');
            element.removeAttribute('data-offen');
            element.setAttribute('aria-hidden', 'true');
            document.removeEventListener('keydown', aufEscape);
            if (zuletztFokussiert) zuletztFokussiert.focus();
        }
        function aufEscape(e) { if (e.key === 'Escape') schliessen(); }

        hintergrund.addEventListener('click', schliessen);
        return { oeffnen: oeffnen, schliessen: schliessen };
    };

    // ── Direktbearbeitung ───────────────────────────────────
    // Elemente mit data-cp-inline="<url>" werden beim Klick editierbar
    // und speichern beim Verlassen. Enter bestaetigt, Escape verwirft.

    cp.inlineAktivieren = function (wurzel) {
        (wurzel || document).querySelectorAll('[data-cp-inline]').forEach(function (el) {
            if (el.dataset.cpInlineBereit) return;
            el.dataset.cpInlineBereit = '1';
            el.classList.add('cp-inline');
            el.setAttribute('contenteditable', 'plaintext-only');
            el.setAttribute('role', 'textbox');
            el.setAttribute('spellcheck', 'false');

            let vorher = el.textContent.trim();

            el.addEventListener('focus', function () { vorher = el.textContent.trim(); });
            el.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') { e.preventDefault(); el.blur(); }
                if (e.key === 'Escape') { el.textContent = vorher; el.blur(); }
            });
            el.addEventListener('blur', function () {
                const neu = el.textContent.trim();
                if (neu === vorher) return;
                if (!neu) { el.textContent = vorher; return; }
                const alt = vorher;
                const feld = el.dataset.cpFeld || 'name';
                const daten = {}; daten[feld] = neu;
                cp.speichern(el.dataset.cpInline, daten).then(function () {
                    vorher = neu;
                    cp.merken('Umbenennen', function () {
                        const zurueck = {}; zurueck[feld] = alt;
                        return cp.speichern(el.dataset.cpInline, zurueck).then(function () {
                            el.textContent = alt;
                            vorher = alt;
                        });
                    });
                    cp.toast('Gespeichert.', { rueckgaengig: cp.rueckgaengig });
                }).catch(function () { el.textContent = alt; });
            });
        });
    };

    document.addEventListener('DOMContentLoaded', function () {
        cp.inlineAktivieren(document);
    });
})();
