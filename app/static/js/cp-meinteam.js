/* ============================================================
   CupPlan – „Mein Team"
   ------------------------------------------------------------
   Eltern und Betreuer stellen am Turniertag immer dieselbe Frage:
   „Wann spielen wir, und wo?" Bisher musste man dafuer jedes Mal
   das Turnier oeffnen, auf den Reiter Spiele tippen und die Liste
   durchsuchen.

   Jetzt: einmal die Mannschaft waehlen, danach steht das naechste
   Spiel ganz oben – mit Uhrzeit, Spielfeld und Gegner. Null Klicks.

   Gespeichert wird nur im Browser (localStorage), je Turnier. Keine
   Konten, keine Daten auf dem Server.
   ============================================================ */

(function () {
    'use strict';

    const cp = window.cp = window.cp || {};
    const SCHLUESSEL = 'cupplan.meinteam.';

    const meinTeam = cp.meinTeam = {

        lesen: function (slug) {
            try {
                const roh = localStorage.getItem(SCHLUESSEL + slug);
                return roh ? JSON.parse(roh) : null;
            } catch (e) { return null; }
        },

        setzen: function (slug, team) {
            try {
                if (team) localStorage.setItem(SCHLUESSEL + slug, JSON.stringify(team));
                else localStorage.removeItem(SCHLUESSEL + slug);
            } catch (e) { /* privater Modus: dann eben ohne Merken */ }
        },

        /* Naechstes und laufendes Spiel der Mannschaft aus dem Zustand. */
        spieleFinden: function (zustand, teamId) {
            if (!zustand || !teamId) return { live: null, naechstes: null, letztes: null };
            const gehoert = function (m) {
                return (m.team1 && m.team1.id === teamId) ||
                       (m.team2 && m.team2.id === teamId);
            };
            const live = (zustand.live_matches || []).filter(gehoert)[0] || null;

            const kommend = []
                .concat(zustand.upcoming_matches || [])
                .concat((zustand.final_matches || []).filter(function (m) {
                    return m.status === 'planned';
                }))
                .filter(gehoert);
            // Nach Anstosszeit, Spiele ohne Zeit zuletzt
            kommend.sort(function (a, b) {
                const za = a.scheduled_time || '~', zb = b.scheduled_time || '~';
                return za < zb ? -1 : za > zb ? 1 : (a.match_order - b.match_order);
            });

            const vergangen = []
                .concat(zustand.past_matches || [])
                .concat((zustand.final_matches || []).filter(function (m) {
                    return m.status === 'finished';
                }))
                .filter(gehoert);

            return { live: live, naechstes: kommend[0] || null,
                     letztes: vergangen[0] || null };
        },

        /* Alle Mannschaften des Turniers aus dem Zustand, alphabetisch. */
        teamsAus: function (zustand) {
            const gesehen = {};
            const liste = [];
            Object.keys(zustand.standings_by_group || {}).forEach(function (gid) {
                (zustand.standings_by_group[gid].standings || []).forEach(function (zeile) {
                    const t = zeile.team;
                    if (t && !gesehen[t.id]) { gesehen[t.id] = 1; liste.push(t); }
                });
            });
            // Teams ohne Gruppe tauchen in keiner Tabelle auf
            [].concat(zustand.live_matches || [], zustand.past_matches || [],
                      zustand.upcoming_matches || [], zustand.final_matches || [])
              .forEach(function (m) {
                  [m.team1, m.team2].forEach(function (t) {
                      if (t && !gesehen[t.id]) { gesehen[t.id] = 1; liste.push(t); }
                  });
              });
            liste.sort(function (a, b) { return a.name.localeCompare(b.name, 'de'); });
            return liste;
        },

        /* Uhrzeit aus dem ISO-Text. Bewusst ohne Date-Objekt: der Server
           liefert lokale Turnierzeit ohne Zeitzone, ein Date wuerde sie
           je nach Geraeteeinstellung verschieben. */
        zeit: function (m) {
            if (!m || !m.scheduled_time) return '';
            const treffer = String(m.scheduled_time).match(/T(\d{2}:\d{2})/);
            return treffer ? treffer[1] : '';
        }
    };
})();
