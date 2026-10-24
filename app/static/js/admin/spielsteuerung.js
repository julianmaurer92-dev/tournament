/* ============================================================
   CupPlan – Spielsteuerung
   ------------------------------------------------------------
   Zwei Dinge sind hier anders als im Rest der App:

   1. Tor mit Torschuetze in zwei Tipps. Der Plus-Knopf oeffnet
      sofort die Spielerliste; ein Tipp auf den Namen traegt Tor
      und Schuetze in einer Anfrage ein. Vorher: neun Schritte
      ueber eine eigene Seite.

   2. Kein Bestaetigungsdialog. Jede Aktion laesst sich mit einem
      Tipp zuruecknehmen. Ein modaler Dialog haelt am Spielfeldrand
      die ganze Seite an, auch die Live-Aktualisierung.
   ============================================================ */

(function () {
    'use strict';

    const zeitEl = document.getElementById('st-zeit');
    const phaseEl = document.getElementById('st-phase');
    const verbindungEl = document.getElementById('st-verbindung');
    const schuetzeEl = document.getElementById('st-schuetze');
    const spielerEl = document.getElementById('st-spieler');

    // Zuletzt benutzte Schuetzen je Team – am Turniertag trifft oft
    // derselbe Spieler mehrfach. Nur im Browser, nichts Gespeichertes.
    const zuletzt = {};

    let zustand = null;           // letzter Zustand vom Server
    let uhrLaeuft = false;
    let uhrRest = 0;
    let uhrSync = 0;
    let uhrTakt = null;

    // ── Uhr ────────────────────────────────────────────────

    function zeitText(sekunden) {
        const s = Math.max(0, Math.round(sekunden));
        return String(Math.floor(s / 60)).padStart(2, '0') + ':' +
               String(s % 60).padStart(2, '0');
    }

    function uhrZeichnen() {
        const rest = uhrLaeuft
            ? Math.max(0, uhrRest - (Date.now() - uhrSync) / 1000)
            : uhrRest;
        zeitEl.textContent = zeitText(rest);
        let art = 'gestoppt';
        if (rest <= 0) art = 'abgelaufen';
        else if (uhrLaeuft && rest <= 30) art = 'kritisch';
        else if (uhrLaeuft && rest <= 60) art = 'warnung';
        else if (uhrLaeuft) art = 'laeuft';
        zeitEl.dataset.zustand = art;
    }

    function uhrStarten() {
        clearInterval(uhrTakt);
        uhrTakt = setInterval(uhrZeichnen, 250);
        uhrZeichnen();
    }

    // ── Zustand uebernehmen ────────────────────────────────

    function spielAusZustand(id) {
        if (!zustand) return null;
        const alle = []
            .concat(zustand.live_matches || [])
            .concat(zustand.past_matches || [])
            .concat(zustand.upcoming_matches || [])
            .concat(zustand.final_matches || []);
        return alle.find(function (m) { return m.id === id; }) || null;
    }

    function anwenden(neu) {
        zustand = neu;
        const spiel = spielAusZustand(SPIEL_ID);
        if (!spiel) return;

        document.querySelectorAll('[data-spiel]').forEach(function (block) {
            const m = spielAusZustand(parseInt(block.dataset.spiel, 10));
            if (!m) return;
            const t1 = block.querySelector('[data-tore="1"]');
            const t2 = block.querySelector('[data-tore="2"]');
            if (t1) t1.textContent = m.score_team1;
            if (t2) t2.textContent = m.score_team2;
        });

        uhrLaeuft = !!spiel.timer_running;
        uhrRest = spiel.timer_remaining;
        uhrSync = Date.now();
        uhrZeichnen();

        const startText = document.getElementById('st-starten-text');
        if (startText) startText.textContent = uhrLaeuft ? 'Läuft' : 'Anpfiff';

        phaseEl.textContent =
            spiel.status === 'finished' ? 'Beendet'
            : spiel.is_penalty ? 'Neunmeterschießen'
            : spiel.is_extra_time ? 'Verlängerung'
            : spiel.status === 'live' ? (uhrLaeuft ? 'Läuft' : 'Unterbrochen')
            : 'Noch nicht angepfiffen';
    }

    // ── Verbindung ─────────────────────────────────────────

    function verbindung(ok, text) {
        if (ok) {
            verbindungEl.removeAttribute('data-sichtbar');
        } else {
            document.getElementById('st-verbindung-text').textContent = text;
            verbindungEl.setAttribute('data-sichtbar', '');
        }
    }

    const socket = io();
    socket.on('connect', function () {
        verbindung(true);
        socket.emit('join_tournament', { tournament_id: TURNIER_ID });
    });
    socket.on('disconnect', function () {
        verbindung(false, 'Keine Verbindung. Eingaben werden nicht gespeichert.');
    });
    socket.on('state_update', function (neu) { verbindung(true); anwenden(neu); });

    // ── Torschuetzen-Auswahl ───────────────────────────────

    let offenesTor = null;

    function schuetzeOeffnen(knopf) {
        const teamId = parseInt(knopf.dataset.team, 10);
        if (!teamId) return;
        offenesTor = {
            spielId: parseInt(knopf.dataset.tor, 10),
            teamId: teamId,
            teamName: knopf.dataset.teamname
        };

        document.getElementById('st-schuetze-unter').textContent =
            'Tor für ' + offenesTor.teamName;

        const namen = (SPIELER[teamId] || []).slice();
        const merker = zuletzt[teamId] || [];
        // Zuletzt benutzte zuerst
        namen.sort(function (a, b) {
            return (merker.indexOf(b) - merker.indexOf(a));
        });

        spielerEl.innerHTML = '';
        namen.forEach(function (name) {
            const teile = name.match(/^\s*(\d+)\s+(.*)$/);
            const knopfEl = document.createElement('button');
            knopfEl.type = 'button';
            knopfEl.className = 'st-spieler-knopf';
            if (merker.indexOf(name) >= 0) knopfEl.dataset.zuletzt = '1';
            if (teile) {
                const nr = document.createElement('span');
                nr.className = 'st-spieler-nr';
                nr.textContent = teile[1];
                knopfEl.appendChild(nr);
                knopfEl.appendChild(document.createTextNode(teile[2]));
            } else {
                knopfEl.textContent = name;
            }
            knopfEl.addEventListener('click', function () { torEintragen(name); });
            spielerEl.appendChild(knopfEl);
        });

        const ohne = document.createElement('button');
        ohne.type = 'button';
        ohne.className = 'st-spieler-knopf st-spieler-knopf--ohne';
        ohne.textContent = namen.length ? 'Ohne Torschütze eintragen'
                                        : 'Tor eintragen (keine Spielerliste hinterlegt)';
        ohne.addEventListener('click', function () { torEintragen(''); });
        spielerEl.appendChild(ohne);

        schuetzeEl.setAttribute('data-offen', '');
        const erstes = spielerEl.querySelector('button');
        if (erstes) erstes.focus();
    }

    function schuetzeSchliessen() {
        schuetzeEl.removeAttribute('data-offen');
        offenesTor = null;
    }

    schuetzeEl.addEventListener('click', function (e) {
        if (e.target === schuetzeEl) schuetzeSchliessen();
    });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && schuetzeEl.hasAttribute('data-offen')) schuetzeSchliessen();
    });

    function standSetzen(spielId, ergebnis) {
        if (!ergebnis) return;
        const block = document.querySelector('[data-spiel="' + spielId + '"]');
        if (!block) return;
        const t1 = block.querySelector('[data-tore="1"]');
        const t2 = block.querySelector('[data-tore="2"]');
        if (t1 && ergebnis.team1 !== undefined) t1.textContent = ergebnis.team1;
        if (t2 && ergebnis.team2 !== undefined) t2.textContent = ergebnis.team2;
    }

    function torEintragen(spielerName) {
        if (!offenesTor) return;
        const daten = offenesTor;
        schuetzeSchliessen();

        if (spielerName) {
            zuletzt[daten.teamId] = (zuletzt[daten.teamId] || [])
                .filter(function (n) { return n !== spielerName; });
            zuletzt[daten.teamId].push(spielerName);
        }

        cp.speichern(
            '/admin/t/' + SLUG + '/api/matches/' + daten.spielId + '/ereignisse',
            { art: 'tor', team_id: daten.teamId, player_name: spielerName,
              ergebnis_anpassen: true }
        ).then(function (antwort) {
            const ereignisId = antwort.ereignis && antwort.ereignis.id;
            const wer = spielerName ? spielerName : daten.teamName;
            // Sofort anzeigen, nicht auf den Rundruf warten. Wenn das
            // WLAN im Sportheim schwach ist, kommt der sonst spaet –
            // und der Zeitnehmer tippt noch einmal.
            standSetzen(daten.spielId, antwort.ergebnis);
            cp.merken('Tor', function () {
                return cp.speichern(
                    '/admin/t/' + SLUG + '/api/ereignisse/' + ereignisId + '/loeschen',
                    { ergebnis_anpassen: true }
                ).then(function (a) { standSetzen(daten.spielId, a.ergebnis); });
            });
            cp.toast('Tor für ' + wer + '.', { rueckgaengig: cp.rueckgaengig });
        });
    }

    document.querySelectorAll('[data-tor]').forEach(function (knopf) {
        knopf.addEventListener('click', function () { schuetzeOeffnen(knopf); });
    });

    // ── Tor zuruecknehmen ueber Minus ──────────────────────

    document.querySelectorAll('[data-minus]').forEach(function (knopf) {
        knopf.addEventListener('click', function () {
            const spielId = parseInt(knopf.dataset.minus, 10);
            const seite = knopf.dataset.seite;
            const m = spielAusZustand(spielId);
            if (!m) return;
            const aktuell = seite === '1' ? m.score_team1 : m.score_team2;
            if (aktuell <= 0) { cp.toast('Steht schon auf null.'); return; }
            const feld = seite === '1' ? 'score_team1' : 'score_team2';
            const daten = {}; daten[feld] = aktuell - 1;
            cp.speichern('/admin/t/' + SLUG + '/api/matches/' + spielId + '/score', daten)
                .then(function (antwort) {
                    standSetzen(spielId, {
                        team1: feld === 'score_team1' ? aktuell - 1 : m.score_team1,
                        team2: feld === 'score_team2' ? aktuell - 1 : m.score_team2
                    });
                    const zurueck = {}; zurueck[feld] = aktuell;
                    cp.merken('Tor abgezogen', function () {
                        return cp.speichern(
                            '/admin/t/' + SLUG + '/api/matches/' + spielId + '/score', zurueck);
                    });
                    cp.toast('Ein Tor abgezogen.', { rueckgaengig: cp.rueckgaengig });
                });
        });
    });

    // ── Uhr bedienen ───────────────────────────────────────

    function timer(aktion, zusatz) {
        const ziele = [SPIEL_ID];
        if (PARALLEL_ID) ziele.push(PARALLEL_ID);
        return Promise.all(ziele.map(function (id) {
            return cp.speichern(
                '/admin/t/' + SLUG + '/api/matches/' + id + '/timer',
                Object.assign({ action: aktion }, zusatz || {}));
        }));
    }

    const startKnopf = document.getElementById('st-starten');
    if (startKnopf) {
        startKnopf.addEventListener('click', function () {
            if (uhrLaeuft) { timer('pause').then(function () { cp.toast('Uhr angehalten.'); }); }
            else { timer('start').then(function () { cp.toast('Anpfiff.'); }); }
        });
    }
    document.getElementById('st-pause').addEventListener('click', function () {
        timer('pause').then(function () { cp.toast('Uhr angehalten.'); });
    });
    document.getElementById('st-zuruecksetzen').addEventListener('click', function () {
        timer('reset').then(function () { cp.toast('Uhr zurückgesetzt.'); });
    });
    document.getElementById('st-verlaengerung').addEventListener('click', function () {
        timer('set', { duration: EXTRA_ZEIT, is_extra_time: true })
            .then(function () { cp.toast('Verlängerung gesetzt.'); });
    });
    document.getElementById('st-neunmeter').addEventListener('click', function () {
        cp.speichern('/admin/t/' + SLUG + '/api/matches/' + SPIEL_ID + '/set-phase',
                     { phase: 'penalty' })
            .then(function () { cp.toast('Neunmeterschießen.'); });
    });

    // ── Beenden und weiter: ein Schritt statt fuenf ────────

    document.getElementById('st-weiter').addEventListener('click', function (e) {
        const knopf = e.currentTarget;
        const spiel = spielAusZustand(SPIEL_ID);
        const schonFertig = spiel && spiel.status === 'finished';

        function weiterGehen() {
            if (NAECHSTES) { location.href = STEUERUNG_URL + NAECHSTES; }
            else { location.href = STAND_URL; }
        }

        if (schonFertig) { weiterGehen(); return; }

        knopf.disabled = true;
        const ziele = [SPIEL_ID];
        if (PARALLEL_ID) ziele.push(PARALLEL_ID);
        Promise.all(ziele.map(function (id) {
            return cp.speichern('/admin/t/' + SLUG + '/api/matches/' + id + '/status',
                                { status: 'finished' });
        })).then(function () {
            // Kurz Zeit zum Zuruecknehmen, bevor die Seite wechselt
            let gewechselt = false;
            const abbrechen = cp.toast('Spiel beendet. Weiter zum nächsten …', {
                dauer: 2600,
                rueckgaengig: function () {
                    gewechselt = true;
                    Promise.all(ziele.map(function (id) {
                        return cp.speichern(
                            '/admin/t/' + SLUG + '/api/matches/' + id + '/status',
                            { status: 'live' });
                    })).then(function () {
                        knopf.disabled = false;
                        cp.toast('Spiel läuft wieder.');
                    });
                }
            });
            setTimeout(function () {
                if (!gewechselt) { if (abbrechen) abbrechen(); weiterGehen(); }
            }, 2600);
        }).catch(function () { knopf.disabled = false; });
    });

    // ── Tastatur am Schreibtisch ───────────────────────────

    document.addEventListener('keydown', function (e) {
        if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
        if (e.metaKey || e.ctrlKey || e.altKey) return;
        if (e.key === ' ') {
            e.preventDefault();
            if (startKnopf) startKnopf.click();
        }
        if (e.key === 'q' || e.key === 'Q') {
            const k = document.querySelector('[data-tor][data-seite="1"]');
            if (k) k.click();
        }
        if (e.key === 'p' || e.key === 'P') {
            const k = document.querySelector('[data-tor][data-seite="2"]');
            if (k) k.click();
        }
    });

    // ── Start ──────────────────────────────────────────────

    uhrStarten();
    fetch('/t/' + SLUG + '/api/state')
        .then(function (r) { return r.json(); })
        .then(anwenden)
        .catch(function () {
            verbindung(false, 'Zustand konnte nicht geladen werden.');
        });
})();
