/* ============================================================
   CupPlan – Befehlspalette (Strg/Cmd + K)
   ------------------------------------------------------------
   Eine Suche ueber alles: Seiten, Aktionen, Mannschaften, Spiele,
   Themes. Tippen, Enter, fertig.

   Bewusst flach, ohne Kategorien zum Durchklicken – wer sucht,
   will tippen, nicht navigieren. Die Herkunft steht als kleiner
   Vermerk rechts, damit man trotzdem weiss, was man trifft.
   ============================================================ */

(function () {
    'use strict';

    const cp = window.cp = window.cp || {};
    if (typeof CP_PALETTE === 'undefined' || !CP_PALETTE.length) return;

    let behaelter = null;
    let feld = null;
    let liste = null;
    let treffer = [];
    let markiert = 0;

    /* Fehlertolerant, aber nicht beliebig: Buchstaben duerfen
       uebersprungen werden – jedoch nur innerhalb eines Wortes.
       "spiplan" findet "Spielplan drucken".

       Die erste Fassung liess Luecken ueber Wortgrenzen hinweg zu.
       Dann fand "smtp" das Spiel "TSV Mettenberg – SpVgg Au": s aus
       TSV, m aus Mettenberg, t aus Mettenberg, p aus SpVgg. Formal
       richtig, als Vorschlag Unsinn. */
    function luecken(wort, suche) {
        let i = 0, punkte = 0;
        for (const z of suche) {
            const gefunden = wort.indexOf(z, i);
            if (gefunden < 0) return -1;
            punkte += gefunden === i ? 3 : 1;
            i = gefunden + 1;
        }
        return punkte;
    }

    function passt(text, suche) {
        if (!suche) return 0;
        text = text.toLowerCase();
        suche = suche.toLowerCase();
        if (text.startsWith(suche)) return 1000;
        const direkt = text.indexOf(suche);
        if (direkt >= 0) return 500 - direkt;
        let beste = -1;
        for (const wort of text.split(/[\s–\-\/()]+/)) {
            if (wort.length < suche.length) continue;
            beste = Math.max(beste, luecken(wort, suche));
        }
        return beste;
    }

    /* Stichwoerter zaehlen weniger als der Name selbst: "Design" soll
       bei der Eingabe "design" vor dem Spielplan stehen, auch wenn der
       das Wort als Stichwort fuehrt. Nur ganze Woerter, keine
       Buchstabenfolgen – sonst trifft jedes Stichwort irgendwas. */
    function stichwortTreffer(eintrag, suche) {
        if (!eintrag.stichwort) return -1;
        const worte = eintrag.stichwort.toLowerCase().split(/\s+/);
        suche = suche.toLowerCase();
        let beste = -1;
        for (const w of worte) {
            if (w.startsWith(suche)) beste = Math.max(beste, 120);
            else if (w.indexOf(suche) >= 0) beste = Math.max(beste, 60);
        }
        return beste;
    }

    function suchen(wort) {
        if (!wort.trim()) return CP_PALETTE.slice(0, 12);
        return CP_PALETTE
            .map(function (e) {
                return { eintrag: e, punkte: Math.max(passt(e.name, wort),
                                                      passt(e.art, wort) - 400,
                                                      stichwortTreffer(e, wort)) };
            })
            .filter(function (x) { return x.punkte > 0; })
            .sort(function (a, b) { return b.punkte - a.punkte; })
            .slice(0, 12)
            .map(function (x) { return x.eintrag; });
    }

    function zeichnen() {
        liste.innerHTML = '';
        if (!treffer.length) {
            const leer = document.createElement('div');
            leer.className = 'pa-leer';
            leer.textContent = 'Nichts gefunden.';
            liste.appendChild(leer);
            return;
        }
        treffer.forEach(function (eintrag, i) {
            const zeile = document.createElement('button');
            zeile.type = 'button';
            zeile.className = 'pa-zeile' + (i === markiert ? ' ist-markiert' : '');
            zeile.setAttribute('role', 'option');
            zeile.setAttribute('aria-selected', i === markiert ? 'true' : 'false');

            const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            icon.setAttribute('class', 'cp-icon');
            icon.setAttribute('viewBox', '0 0 24 24');
            icon.setAttribute('aria-hidden', 'true');
            const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
            use.setAttribute('href', CP_SPRITE + '#i-' + (eintrag.icon || 'chevron-right'));
            icon.appendChild(use);
            zeile.appendChild(icon);

            const name = document.createElement('span');
            name.className = 'pa-name';
            name.textContent = eintrag.name;
            zeile.appendChild(name);

            const art = document.createElement('span');
            art.className = 'pa-art';
            art.textContent = eintrag.art;
            zeile.appendChild(art);

            zeile.addEventListener('click', function () { waehlen(i); });
            zeile.addEventListener('mousemove', function () {
                if (markiert !== i) { markiert = i; zeichnen(); }
            });
            liste.appendChild(zeile);
        });
    }

    function waehlen(i) {
        const eintrag = treffer[i];
        if (!eintrag) return;
        schliessen();
        location.href = eintrag.ziel;
    }

    function aufbauen() {
        behaelter = document.createElement('div');
        behaelter.className = 'pa-hintergrund';
        behaelter.innerHTML = `
            <div class="pa-fenster" role="dialog" aria-modal="true" aria-label="Suche">
                <div class="pa-kopf">
                    <svg class="cp-icon" aria-hidden="true"><use href="${CP_SPRITE}#i-search"></use></svg>
                    <input type="text" class="pa-feld" id="pa-feld" autocomplete="off"
                           spellcheck="false" placeholder="Seite, Mannschaft, Spiel, Theme …"
                           role="combobox" aria-expanded="true" aria-controls="pa-liste">
                    <kbd class="pa-kbd">Esc</kbd>
                </div>
                <div class="pa-liste" id="pa-liste" role="listbox" aria-label="Treffer"></div>
                <div class="pa-fuss">
                    <span><kbd class="pa-kbd">↑</kbd><kbd class="pa-kbd">↓</kbd> wählen</span>
                    <span><kbd class="pa-kbd">↵</kbd> öffnen</span>
                </div>
            </div>`;
        document.body.appendChild(behaelter);
        feld = behaelter.querySelector('#pa-feld');
        liste = behaelter.querySelector('#pa-liste');

        behaelter.addEventListener('click', function (e) {
            if (e.target === behaelter) schliessen();
        });
        feld.addEventListener('input', function () {
            treffer = suchen(feld.value);
            markiert = 0;
            zeichnen();
        });
        feld.addEventListener('keydown', function (e) {
            if (e.key === 'ArrowDown') {
                e.preventDefault(); markiert = (markiert + 1) % Math.max(1, treffer.length); zeichnen();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault(); markiert = (markiert - 1 + treffer.length) % Math.max(1, treffer.length); zeichnen();
            } else if (e.key === 'Enter') {
                e.preventDefault(); waehlen(markiert);
            } else if (e.key === 'Escape') {
                e.preventDefault(); schliessen();
            }
        });
    }

    let zuletztFokussiert = null;

    function oeffnen() {
        if (!behaelter) aufbauen();
        zuletztFokussiert = document.activeElement;
        behaelter.setAttribute('data-offen', '');
        feld.value = '';
        treffer = suchen('');
        markiert = 0;
        zeichnen();
        feld.focus();
    }

    function schliessen() {
        if (!behaelter) return;
        behaelter.removeAttribute('data-offen');
        if (zuletztFokussiert && zuletztFokussiert.focus) zuletztFokussiert.focus();
    }

    cp.palette = { oeffnen: oeffnen, schliessen: schliessen };

    document.addEventListener('keydown', function (e) {
        const istK = e.key === 'k' || e.key === 'K';
        if (istK && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            behaelter && behaelter.hasAttribute('data-offen') ? schliessen() : oeffnen();
            return;
        }
        // "?" oeffnet die Tastenuebersicht – aber nicht, waehrend man tippt
        if (e.key === '?' && !/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)
                && !e.target.isContentEditable) {
            e.preventDefault();
            tastenUebersicht();
        }
    });

    /* ── Tastenuebersicht ───────────────────────────────── */

    const TASTEN = [
        ['Strg / Cmd + K', 'Suche über alles öffnen'],
        ['?',              'Diese Übersicht'],
        ['Strg / Cmd + Z', 'Letzte Änderung rückgängig'],
        ['Leertaste',      'Spielsteuerung: anpfeifen oder anhalten'],
        ['Q',              'Spielsteuerung: Tor für die linke Mannschaft'],
        ['P',              'Spielsteuerung: Tor für die rechte Mannschaft'],
        ['← →',            'Beamer-Ansicht: Seite wechseln'],
        ['Esc',            'Schließen'],
    ];

    function tastenUebersicht() {
        const alt = document.querySelector('.pa-tasten');
        if (alt) { alt.remove(); return; }
        const el = document.createElement('div');
        el.className = 'pa-hintergrund pa-tasten';
        el.setAttribute('data-offen', '');
        el.innerHTML = `
            <div class="pa-fenster" role="dialog" aria-modal="true" aria-label="Tastenkürzel">
                <div class="pa-kopf"><strong class="pa-name">Tastenkürzel</strong>
                    <kbd class="pa-kbd">Esc</kbd></div>
                <div class="pa-liste">
                    ${TASTEN.map(function (t) {
                        return `<div class="pa-zeile"><span class="pa-name">${t[1]}</span>
                                <kbd class="pa-kbd">${t[0]}</kbd></div>`;
                    }).join('')}
                </div>
            </div>`;
        document.body.appendChild(el);
        el.addEventListener('click', function (e) { if (e.target === el) el.remove(); });
        const zu = function (e) {
            if (e.key === 'Escape') { el.remove(); document.removeEventListener('keydown', zu); }
        };
        document.addEventListener('keydown', zu);
    }
})();
