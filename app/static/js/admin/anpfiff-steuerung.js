/* ============================================================
   ANPFIFF – Spielsteuerung
   ------------------------------------------------------------
   Vier Dinge bestimmen den Aufbau:

   1. TOR MIT SCHÜTZE IN ZWEI TIPPS. Der große Tor-Knopf öffnet
      sofort die Schützenliste; ein Tipp auf den Namen trägt Tor
      und Schütze in EINER Anfrage ein.

   2. SOFORT IM BILD. Der Spielstand wird aus der Antwort gesetzt,
      nicht aus dem Rundruf. Im Sportheim-WLAN kann der dauern –
      und wer nichts passieren sieht, tippt noch einmal.

   3. KEIN DIALOG, SONDERN RÜCKGÄNGIG. Alles lässt sich mit einem
      Tipp zurücknehmen.

   4. ZWEI FELDER GLEICHZEITIG. Jede Partie hat ihre eigenen
      Knöpfe; die Uhr gilt für beide.
   ============================================================ */

(function () {
    'use strict';

    const uhrEl = document.getElementById('st-uhr');
    const zeitEl = document.getElementById('st-zeit');
    const verbindungEl = document.getElementById('st-verbindung');

    const SPIELE = [SPIEL_ID].concat(PARALLEL_ID ? [PARALLEL_ID] : []);

    // Zuletzt benutzte Schützen je Mannschaft. Im selben Spiel
    // trifft oft derselbe mehrfach – dann steht er oben.
    const zuletzt = {};

    let zustand = null;
    let uhrLaeuft = false;
    let uhrRest = 0;
    let uhrSync = 0;
    let uhrTakt = null;

    /* ── Uhr ───────────────────────────────────────────────── */

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
        // Der Zustand steckt in der Farbe, nicht in einem Wort daneben.
        let art = 'bereit';
        if (rest <= 0 && uhrRest > 0) art = 'aus';
        else if (uhrLaeuft && rest <= 30) art = 'schluss';
        else if (uhrLaeuft && rest <= 60) art = 'letzte';
        else if (uhrLaeuft) art = 'laeuft';
        uhrEl.dataset.zustand = art;
    }

    function uhrTakten() {
        clearInterval(uhrTakt);
        uhrTakt = setInterval(uhrZeichnen, 250);
        uhrZeichnen();
    }

    /* ── Zustand anwenden ──────────────────────────────────── */

    function spielAus(id) {
        if (!zustand) return null;
        const alle = [].concat(zustand.live_matches || [], zustand.past_matches || [],
                               zustand.upcoming_matches || [], zustand.final_matches || []);
        return alle.filter(function (m) { return m.id === id; })[0] || null;
    }

    function block(id) {
        return document.querySelector('[data-spiel="' + id + '"]');
    }

    function standSetzen(id, ergebnis) {
        const b = block(id);
        if (!b || !ergebnis) return;
        [['tore1', 'team1'], ['tore2', 'team2']].forEach(function (paar) {
            const el = b.querySelector('[data-rolle="' + paar[0] + '"]');
            const neu = ergebnis[paar[1]];
            if (el && neu !== undefined && el.textContent !== String(neu)) {
                el.textContent = neu;
                ap.hervorheben(el);
            }
        });
    }

    function anwenden(neu) {
        zustand = neu;

        SPIELE.forEach(function (id) {
            const m = spielAus(id);
            const b = block(id);
            if (!m || !b) return;
            standSetzen(id, { team1: m.score_team1 || 0, team2: m.score_team2 || 0 });

            if (m.status === 'finished') b.setAttribute('data-fertig', '');
            else b.removeAttribute('data-fertig');

            const abz = b.querySelector('[data-rolle="abzeichen"]');
            if (abz) {
                const art = m.status === 'live' ? 'live'
                          : m.status === 'finished' ? 'fertig' : '';
                const text = m.status === 'live' ? 'Läuft'
                           : m.status === 'finished' ? 'Beendet' : 'Geplant';
                abz.innerHTML = '<span class="ap-abzeichen ' +
                    (art ? 'ap-abzeichen--' + art : '') + '">' +
                    (art === 'live' ? '<span class="ap-puls"></span>' : '') +
                    text + '</span>';
            }

            const uhrText = b.querySelector('[data-rolle="uhr-text"]');
            if (uhrText) uhrText.textContent = m.timer_running ? 'Anhalten' : 'Anpfiff';
        });

        // Die Uhr des Hauptspiels gilt für die Anzeige oben
        const haupt = spielAus(SPIEL_ID);
        if (haupt) {
            uhrLaeuft = !!haupt.timer_running;
            uhrRest = haupt.timer_remaining || 0;
            uhrSync = Date.now();
            uhrZeichnen();
        }
    }

    /* ── Tor mit Schütze: zwei Tipps ───────────────────────── */

    function schuetzeOeffnen(spielId, seite) {
        const m = spielAus(spielId);
        if (!m) return;
        const team = seite === 1 ? m.team1 : m.team2;
        if (!team) return;

        const liste = (SPIELER[team.id] || []).slice();
        const oben = (zuletzt[team.id] || []).slice().reverse();
        const sortiert = oben.concat(liste.filter(function (n) {
            return oben.indexOf(n) < 0;
        }));

        const kasten = document.createElement('div');
        kasten.className = 'st-schuetzen';

        function eintragen(name) {
            schublade.schliessen();
            torEintragen(spielId, team, name);
        }

        sortiert.forEach(function (name) {
            const k = document.createElement('button');
            k.type = 'button';
            k.className = 'st-schuetze' + (oben.indexOf(name) >= 0 ? ' st-schuetze--zuletzt' : '');
            k.textContent = name;
            k.addEventListener('click', function () { eintragen(name); });
            kasten.appendChild(k);
        });

        const ohne = document.createElement('button');
        ohne.type = 'button';
        ohne.className = 'st-schuetze st-schuetze--ohne';
        ohne.textContent = sortiert.length ? 'Ohne Schützen eintragen'
                                           : 'Tor eintragen (keine Spieler hinterlegt)';
        ohne.addEventListener('click', function () { eintragen(''); });
        kasten.appendChild(ohne);

        const schublade = ap.schublade('Wer hat getroffen?', kasten);
    }

    function torEintragen(spielId, team, name) {
        if (name) {
            zuletzt[team.id] = (zuletzt[team.id] || [])
                .filter(function (n) { return n !== name; });
            zuletzt[team.id].push(name);
        }

        ap.speichern('/admin/t/' + SLUG + '/api/matches/' + spielId + '/ereignisse',
                     { art: 'tor', team_id: team.id, player_name: name,
                       ergebnis_anpassen: true })
            .then(function (antwort) {
                const ereignisId = antwort.ereignis && antwort.ereignis.id;
                standSetzen(spielId, antwort.ergebnis);
                ap.merken('Tor', function () {
                    return ap.speichern(
                        '/admin/t/' + SLUG + '/api/ereignisse/' + ereignisId + '/loeschen',
                        { ergebnis_anpassen: true }
                    ).then(function (a) { standSetzen(spielId, a.ergebnis); });
                });
                ap.meldung('Tor für ' + (name || team.name) + '.',
                           { rueckgaengig: ap.rueckgaengig });
            });
    }

    /* ── Tor abziehen ──────────────────────────────────────── */

    function torAbziehen(spielId, seite) {
        const m = spielAus(spielId);
        if (!m) return;
        const feld = seite === 1 ? 'score_team1' : 'score_team2';
        const aktuell = m[feld] || 0;
        if (aktuell <= 0) { ap.meldung('Steht schon auf null.'); return; }

        const daten = {}; daten[feld] = aktuell - 1;
        ap.speichern('/admin/t/' + SLUG + '/api/matches/' + spielId + '/score', daten)
            .then(function () {
                standSetzen(spielId, {
                    team1: seite === 1 ? aktuell - 1 : (m.score_team1 || 0),
                    team2: seite === 2 ? aktuell - 1 : (m.score_team2 || 0)
                });
                const zurueck = {}; zurueck[feld] = aktuell;
                ap.merken('Tor abgezogen', function () {
                    return ap.speichern(
                        '/admin/t/' + SLUG + '/api/matches/' + spielId + '/score', zurueck);
                });
                ap.meldung('Ein Tor abgezogen.', { rueckgaengig: ap.rueckgaengig });
            });
    }

    /* ── Uhr bedienen ──────────────────────────────────────── */
    /* Die Uhr gilt für beide Felder: Auf einem Jugendturnier
       starten Partien auf Feld 1 und 2 gemeinsam. */

    function uhrAktion(aktion, zusatz) {
        return Promise.all(SPIELE.map(function (id) {
            return ap.speichern('/admin/t/' + SLUG + '/api/matches/' + id + '/timer',
                                Object.assign({ action: aktion }, zusatz || {}));
        }));
    }

    /* ── Beenden und weiter ────────────────────────────────── */

    function beenden() {
        const ziele = SPIELE.slice();
        Promise.all(ziele.map(function (id) {
            return ap.speichern('/admin/t/' + SLUG + '/api/matches/' + id + '/status',
                                { status: 'finished' });
        })).then(function () {
            let gesprungen = false;
            ap.merken('Spiel beendet', function () {
                gesprungen = true;
                return Promise.all(ziele.map(function (id) {
                    return ap.speichern('/admin/t/' + SLUG + '/api/matches/' + id + '/status',
                                        { status: 'live' });
                }));
            });
            ap.meldung(NAECHSTES ? 'Beendet. Weiter zum nächsten Spiel …'
                                 : 'Spiel beendet.',
                       { rueckgaengig: ap.rueckgaengig, dauer: 2600 });
            // Kurz warten, damit „Rückgängig" eine Chance hat.
            if (NAECHSTES) {
                setTimeout(function () {
                    if (!gesprungen) {
                        location.href = '/admin/t/' + SLUG + '/matches/' + NAECHSTES + '/control';
                    }
                }, 2600);
            }
        });
    }

    /* ── Knöpfe verdrahten ─────────────────────────────────── */

    SPIELE.forEach(function (id) {
        const b = block(id);
        if (!b) return;
        [1, 2].forEach(function (seite) {
            const tor = b.querySelector('[data-rolle="tor' + seite + '"]');
            if (tor) tor.addEventListener('click', function () { schuetzeOeffnen(id, seite); });
            const minus = b.querySelector('[data-rolle="minus' + seite + '"]');
            if (minus) minus.addEventListener('click', function () { torAbziehen(id, seite); });
        });
        const uhr = b.querySelector('[data-rolle="uhr"]');
        if (uhr) uhr.addEventListener('click', function () {
            if (uhrLaeuft) uhrAktion('pause').then(function () { ap.meldung('Uhr angehalten.'); });
            else uhrAktion('start').then(function () { ap.meldung('Anpfiff.'); });
        });
        const ende = b.querySelector('[data-rolle="beenden"]');
        if (ende) ende.addEventListener('click', beenden);
    });

    const verl = document.querySelector('[data-rolle="verlaengerung"]');
    if (verl) verl.addEventListener('click', function () {
        uhrAktion('set', { duration: EXTRA_ZEIT, is_extra_time: true })
            .then(function () { ap.meldung('Verlängerung gesetzt.'); });
    });

    const karte = document.querySelector('[data-rolle="karte"]');
    if (karte) karte.addEventListener('click', karteOeffnen);

    function karteOeffnen() {
        const m = spielAus(SPIEL_ID);
        if (!m) return;
        const kasten = document.createElement('div');
        kasten.className = 'ap-stapel';
        [['gelb', 'Gelbe Karte'], ['gelb_rot', 'Gelb-Rote Karte'], ['rot', 'Rote Karte']]
            .forEach(function (paar) {
                [m.team1, m.team2].forEach(function (team) {
                    if (!team) return;
                    const k = document.createElement('button');
                    k.type = 'button';
                    k.className = 'ap-knopf ap-knopf--breit';
                    k.innerHTML = '<span class="ap-karten"><span class="ap-karte ap-karte--' +
                        paar[0].replace('_', '') + '"></span></span> ' +
                        paar[1] + ' · ' + team.name;
                    k.addEventListener('click', function () {
                        schublade.schliessen();
                        ap.speichern('/admin/t/' + SLUG + '/api/matches/' + SPIEL_ID + '/ereignisse',
                                     { art: paar[0], team_id: team.id, player_name: '' })
                            .then(function (antwort) {
                                const eid = antwort.ereignis && antwort.ereignis.id;
                                ap.merken(paar[1], function () {
                                    return ap.speichern(
                                        '/admin/t/' + SLUG + '/api/ereignisse/' + eid + '/loeschen', {});
                                });
                                ap.meldung(paar[1] + ' für ' + team.name + '.',
                                           { rueckgaengig: ap.rueckgaengig });
                            });
                    });
                    kasten.appendChild(k);
                });
            });
        const schublade = ap.schublade('Karte eintragen', kasten);
    }

    /* ── Tastatur am Schreibtisch ──────────────────────────── */

    document.addEventListener('keydown', function (e) {
        if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
        if (e.metaKey || e.ctrlKey || e.altKey) return;
        if (e.key === ' ') {
            e.preventDefault();
            if (uhrLaeuft) uhrAktion('pause'); else uhrAktion('start');
        } else if (e.key === 'q' || e.key === 'Q') {
            e.preventDefault(); schuetzeOeffnen(SPIEL_ID, 1);
        } else if (e.key === 'p' || e.key === 'P') {
            e.preventDefault(); schuetzeOeffnen(SPIEL_ID, 2);
        }
    });

    /* ── Verbindung ────────────────────────────────────────── */

    const socket = io();
    socket.on('connect', function () {
        socket.emit('join_tournament', { tournament_id: TURNIER_ID });
        verbindungEl.removeAttribute('data-weg');
    });
    socket.on('disconnect', function () { verbindungEl.setAttribute('data-weg', ''); });
    socket.on('state_update', anwenden);

    // Fällt der Rundruf aus, holen wir den Zustand selbst.
    setInterval(function () {
        if (!socket.connected) {
            fetch('/t/' + SLUG + '/api/state')
                .then(function (r) { return r.json(); })
                .then(anwenden)
                .catch(function () {});
        }
    }, 10000);

    fetch('/t/' + SLUG + '/api/state')
        .then(function (r) { return r.json(); })
        .then(anwenden)
        .catch(function () {});

    uhrTakten();
})();
