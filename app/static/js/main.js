// ============================================================
// Jugendfussballturnier – Frontend Controller
// WebSocket + live timer + dynamic theming + stacked standings
// + bracket rendering + phase logic + winner display
// + multi-tournament room support
// ============================================================

const socket = io();

let currentState = null;
let localTimerInterval = null;
let localTimerRemaining = 0;
let localTimerRunning = false;
let localTimerServerSync = 0;

// ──────────────────────────────────────
// Socket events
// ──────────────────────────────────────

socket.on('connect', () => {
    console.log('[WS] connected');
    // Join tournament-specific room
    if (typeof TOURNAMENT_ID !== 'undefined') {
        socket.emit('join_tournament', {tournament_id: TOURNAMENT_ID});
    }
});

socket.on('state_update', (state) => {
    currentState = state;
    applySettings(state.settings);
    render(state);
});

socket.on('disconnect', () => {
    console.log('[WS] disconnected');
});

// Fallback HTTP polling every 10s if WebSocket drops
setInterval(() => {
    if (!socket.connected && typeof TOURNAMENT_SLUG !== 'undefined') {
        fetch(`/t/${TOURNAMENT_SLUG}/api/state`)
            .then(r => r.json())
            .then(state => {
                currentState = state;
                applySettings(state.settings);
                render(state);
            })
            .catch(() => {});
    }
}, 10000);

// ──────────────────────────────────────
// Dynamic theming from settings
// ──────────────────────────────────────

function applySettings(settings) {
    if (!settings) return;

    const root = document.documentElement;
    if (settings.color_primary)   root.style.setProperty('--color-primary', settings.color_primary);
    if (settings.color_secondary) root.style.setProperty('--color-secondary', settings.color_secondary);
    if (settings.color_title)     root.style.setProperty('--color-title', settings.color_title);

    if (settings.tournament_name) {
        const nameEl = document.getElementById('tournament-name');
        if (nameEl) nameEl.textContent = settings.tournament_name;
        document.title = settings.tournament_name + ' - Live';
    }

    // Announcement banner
    renderAnnouncement(settings.announcement);
}

function renderAnnouncement(text) {
    let banner = document.getElementById('announcement-banner');
    if (!text || text.trim() === '') {
        if (banner) banner.remove();
        return;
    }
    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'announcement-banner';
        banner.className = 'announcement-banner';
        const header = document.querySelector('.main-header');
        if (header && header.nextSibling) {
            header.parentNode.insertBefore(banner, header.nextSibling);
        } else {
            document.body.prepend(banner);
        }
    }
    banner.innerHTML = `<span class="announcement-icon">&#128226;</span><span class="announcement-text">${esc(text)}</span>`;
}

// ──────────────────────────────────────
// Render functions
// ──────────────────────────────────────

function render(state) {
    const phase = (state.settings && state.settings.tournament_phase) || 'GROUP_STAGE';
    const hideResults = (state.settings && state.settings.hide_results === '1');
    const layout = document.querySelector('.layout');

    // Toggle layout class for finals
    if (layout) {
        layout.classList.toggle('layout-finals', phase === 'FINAL_ROUND' || phase === 'FINISHED');
    }

    renderLiveMatch(state.live_matches && state.live_matches.length ? state.live_matches : (state.live_match ? [state.live_match] : []), hideResults);
    renderPastMatches(state.past_matches, hideResults);
    renderUpcomingMatches(state.upcoming_matches);
    renderStandings(state.standings_by_group, state.groups, hideResults);
    renderBracket(state.final_matches || [], phase, hideResults);
    renderWinner(state.final_matches || [], phase, hideResults);
}

function buildLiveCard(match, hideResults, showFieldLabel, timerId, compact) {
    const labelTag = match.final_label
        ? `<span class="live-final-label">${esc(match.final_label)}</span>`
        : '';
    const fieldTag = showFieldLabel
        ? `<span class="live-field-label">Spielfeld ${match.field || 1}</span>`
        : '';
    const groupTag = match.group_name
        ? `<span style="font-size:0.7rem;color:var(--text-muted);margin-top:0.3rem;display:block">${esc(match.group_name)}</span>`
        : '';
    const extraTimeTag = match.is_extra_time
        ? `<span class="extra-time-badge">&#9201; Verlaengerung</span>`
        : match.is_penalty
        ? `<span class="extra-time-badge" style="background:rgba(239,68,68,0.15);border-color:#ef4444;color:#ef4444">&#9917; Elfmeterschiessen</span>`
        : '';
    const scoreHtml = hideResults
        ? `<div class="live-score"><span class="divider">vs</span></div>`
        : `<div class="live-score">
                <span>${match.score_team1}</span>
                <span class="divider">:</span>
                <span>${match.score_team2}</span>
           </div>`;
    const cardClass = compact ? 'live-card live-card-compact' : 'live-card';
    return `
        <div class="${cardClass}">
            <span class="live-badge">LIVE</span>
            ${fieldTag}${extraTimeTag}${labelTag}
            <div class="live-teams">
                <div class="live-team">
                    ${teamLogo(match.team1, compact ? 'sm' : 'lg')}
                    <span class="live-team-name">${match.team1 ? esc(match.team1.name) : 'TBD'}</span>
                </div>
                ${scoreHtml}
                <div class="live-team">
                    ${teamLogo(match.team2, compact ? 'sm' : 'lg')}
                    <span class="live-team-name">${match.team2 ? esc(match.team2.name) : 'TBD'}</span>
                </div>
            </div>
            <div id="${timerId}" class="live-timer">${formatTime(match.timer_remaining)}</div>
            ${groupTag}
        </div>`;
}

function renderLiveMatch(matches, hideResults) {
    const container = document.getElementById('live-match');
    if (!matches || matches.length === 0) {
        container.innerHTML = `
            <div class="no-live-match">
                <div class="no-live-icon">&#9917;</div>
                <p>Kein Spiel aktiv</p>
                <p class="no-live-sub">Warte auf den Anpfiff...</p>
            </div>`;
        stopLocalTimer();
        renderNextMatchPrep(0);
        return;
    }

    const showFieldLabel = matches.length > 1;

    // Sync primary timer from first match (field 1)
    const primary = matches[0];
    localTimerRemaining = primary.timer_remaining;
    localTimerRunning = primary.timer_running;
    localTimerServerSync = Date.now();
    if (localTimerRunning) startLocalTimer(); else stopLocalTimer();

    if (matches.length === 1) {
        container.style.cssText = '';
        container.innerHTML = buildLiveCard(primary, hideResults, false, 'live-timer', false);
    } else {
        container.style.cssText = 'display:grid;grid-template-columns:repeat(' + matches.length + ',1fr);gap:1rem';
        container.innerHTML = matches.map((m, i) =>
            buildLiveCard(m, hideResults, true, 'live-timer-' + i, true)
        ).join('');
    }
    updateTimerClass();
    renderNextMatchPrep(localTimerRemaining);
}

// ──────────────────────────────────────
// Anstosszeit / Spielfeld
// ──────────────────────────────────────

// "2026-11-14T09:15:00" -> "09:15". Bewusst ohne Date-Objekt: der Server
// liefert lokale Turnierzeit ohne Zeitzone, und ein new Date() wuerde sie
// je nach Geraet verschieben.
function matchTime(m) {
    if (!m || !m.scheduled_time) return '';
    const treffer = String(m.scheduled_time).match(/T(\d{2}:\d{2})/);
    return treffer ? treffer[1] : '';
}

// Zeit und – bei mehreren Feldern – Feldnummer als kleine Zeile
function matchMeta(m, numFields) {
    const zeit = matchTime(m);
    const teile = [];
    if (zeit) teile.push(zeit);
    if (numFields > 1 && m.field) teile.push('Feld ' + m.field);
    if (!teile.length) return '';
    return `<span class="match-meta">${teile.join(' &middot; ')}</span>`;
}

function renderPastMatches(matches, hideResults) {
    const container = document.getElementById('past-matches');
    if (!matches || matches.length === 0) {
        container.innerHTML = '<p class="empty-state">Noch keine Spiele beendet</p>';
        return;
    }
    const numFields = parseInt((currentState && currentState.settings
        && currentState.settings.num_fields) || 1, 10);
    container.innerHTML = matches.map(m => `
        <div class="match-item finished">
            <span class="team-name">${teamLogo(m.team1, 'sm')}${m.team1 ? esc(m.team1.name) : 'TBD'}</span>
            <span class="match-score">${hideResults ? '&#10003;' : m.score_team1 + ' : ' + m.score_team2}</span>
            <span class="team-name">${teamLogo(m.team2, 'sm')}${m.team2 ? esc(m.team2.name) : 'TBD'}</span>
            ${matchMeta(m, numFields)}
        </div>
    `).join('');
}

function renderUpcomingMatches(matches) {
    const container = document.getElementById('upcoming-matches');
    if (!matches || matches.length === 0) {
        container.innerHTML = '<p class="empty-state">Keine Spiele geplant</p>';
        return;
    }
    const numFields = parseInt((currentState && currentState.settings
        && currentState.settings.num_fields) || 1, 10);
    container.innerHTML = matches.map((m, i) => `
        <div class="match-item planned${i === 0 ? ' next-match' : ''}">
            <span class="team-name">${teamLogo(m.team1, 'sm')}${m.team1 ? esc(m.team1.name) : 'TBD'}</span>
            <span class="match-score">${matchTime(m) || 'vs'}</span>
            <span class="team-name">${teamLogo(m.team2, 'sm')}${m.team2 ? esc(m.team2.name) : 'TBD'}</span>
            ${numFields > 1 && m.field ? `<span class="match-meta">Feld ${m.field}</span>` : ''}
        </div>
    `).join('');
}

function renderNextMatchPrep(remaining) {
    const container = document.getElementById('next-match-prep');
    if (!container) return;

    // Show prep card when timer is running and <= 4 minutes remain
    const show = localTimerRunning && remaining <= 240 && remaining > 0
        && currentState && currentState.upcoming_matches && currentState.upcoming_matches.length > 0;

    if (!show) {
        container.innerHTML = '';
        return;
    }

    const next = currentState.upcoming_matches[0];
    const t1 = next.team1 ? esc(next.team1.name) : 'TBD';
    const t2 = next.team2 ? esc(next.team2.name) : 'TBD';
    const t1Logo = teamLogo(next.team1, 'lg');
    const t2Logo = teamLogo(next.team2, 'lg');

    container.innerHTML = `
        <div class="next-match-card">
            <div class="next-match-label">
                &#128226; Nächstes Spiel &ndash; Bitte vorbereiten!
                ${matchTime(next) ? ' (' + matchTime(next) + ' Uhr)' : ''}
            </div>
            <div class="next-match-teams">
                <div class="next-match-team">
                    ${t1Logo}
                    <span class="next-match-name">${t1}</span>
                </div>
                <span class="next-match-vs">vs</span>
                <div class="next-match-team">
                    ${t2Logo}
                    <span class="next-match-name">${t2}</span>
                </div>
            </div>
        </div>`;
}

function renderStandings(standingsByGroup, groups, hideResults) {
    const container = document.getElementById('standings');
    if (hideResults) {
        container.innerHTML = '';
        container.style.display = 'none';
        return;
    }
    container.style.display = '';
    if (!standingsByGroup || !groups || groups.length === 0) {
        container.innerHTML = '<p class="empty-state">Keine Teams registriert</p>';
        return;
    }

    let html = '';
    groups.forEach(g => {
        const groupData = standingsByGroup[g.id];
        if (!groupData || !groupData.standings || groupData.standings.length === 0) return;

        const standings = groupData.standings;
        html += `
            <section class="panel standings-group-panel">
                <h2 class="panel-title">${esc(g.name)}</h2>
                <table class="standings-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>TEAM</th>
                            <th>SP</th>
                            <th>S</th>
                            <th>U</th>
                            <th>N</th>
                            <th>T</th>
                            <th>TD</th>
                            <th>P</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${standings.map(s => `
                            <tr>
                                <td class="rank-cell">${s.rank}</td>
                                <td class="team-cell">${teamLogo(s.team, 'xs')}${esc(s.team.name)}</td>
                                <td>${s.played}</td>
                                <td>${s.won}</td>
                                <td>${s.drawn}</td>
                                <td>${s.lost}</td>
                                <td>${s.goals_for}:${s.goals_against}</td>
                                <td>${s.goal_diff > 0 ? '+' : ''}${s.goal_diff}</td>
                                <td class="pts-cell">${s.points}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </section>`;
    });

    if (!html) {
        container.innerHTML = '<p class="empty-state">Keine Teams registriert</p>';
        return;
    }
    container.innerHTML = html;
}

// ──────────────────────────────────────
// Bracket rendering
// ──────────────────────────────────────

function renderBracket(finalMatches, phase, hideResults) {
    const container = document.getElementById('bracket-container');
    if (!container) return;

    if (!finalMatches || finalMatches.length === 0 || phase === 'GROUP_STAGE') {
        container.innerHTML = '';
        return;
    }

    // Separate regular bracket matches from loser/Platz3 matches
    const bracketMatches = finalMatches.filter(m => !m.is_loser_match);
    const loserMatches = finalMatches.filter(m => m.is_loser_match);

    // Group by round (final_round: 4=AF, 3=VF, 2=HF, 1=Finale)
    const rounds = {};
    bracketMatches.forEach(m => {
        const r = m.final_round || 1;
        if (!rounds[r]) rounds[r] = [];
        rounds[r].push(m);
    });

    // Sort rounds descending (highest round number = earliest round)
    const roundKeys = Object.keys(rounds).map(Number).sort((a, b) => b - a);

    const ROUND_NAMES = { 1: 'Finale', 2: 'Halbfinale', 3: 'Viertelfinale', 4: 'Achtelfinale' };

    let html = '<div class="bracket">';

    roundKeys.forEach(rk => {
        const matches = rounds[rk].sort((a, b) => (a.final_position || 0) - (b.final_position || 0));
        html += `<div class="bracket-round">`;
        html += `<div class="bracket-round-title">${ROUND_NAMES[rk] || 'Runde ' + rk}</div>`;
        matches.forEach(m => {
            html += renderBracketMatch(m, hideResults);
        });
        html += `</div>`;
    });

    html += '</div>';

    // Loser bracket (Platz 3)
    if (loserMatches.length > 0) {
        html += '<div class="bracket-platz3">';
        html += '<div class="bracket-round-title">Spiel um Platz 3</div>';
        loserMatches.forEach(m => {
            html += renderBracketMatch(m, hideResults);
        });
        html += '</div>';
    }

    container.innerHTML = html;
}

function renderBracketMatch(m, hideResults) {
    const t1Name = m.team1 ? esc(m.team1.name) : 'TBD';
    const t2Name = m.team2 ? esc(m.team2.name) : 'TBD';
    const isFinished = m.status === 'finished';
    const isLive = m.status === 'live';

    let t1Class = 'bracket-team';
    let t2Class = 'bracket-team';

    if (!hideResults && isFinished) {
        if (m.score_team1 > m.score_team2) t1Class += ' bracket-winner';
        else if (m.score_team2 > m.score_team1) t2Class += ' bracket-winner';
    }

    const statusClass = isLive ? ' bracket-match-live' : isFinished ? ' bracket-match-finished' : '';
    const liveIndicator = isLive ? '<span class="bracket-live-dot"></span>' : '';

    const t1Logo = m.team1 ? teamLogo(m.team1, 'xs') : '';
    const t2Logo = m.team2 ? teamLogo(m.team2, 'xs') : '';

    const showScore = !hideResults && (isFinished || isLive);

    return `
        <div class="bracket-match${statusClass}">
            ${liveIndicator}
            <div class="${t1Class}">
                ${t1Logo}<span class="bracket-team-name">${t1Name}</span>
                <span class="bracket-team-score">${showScore ? m.score_team1 : ''}</span>
            </div>
            <div class="${t2Class}">
                ${t2Logo}<span class="bracket-team-name">${t2Name}</span>
                <span class="bracket-team-score">${showScore ? m.score_team2 : ''}</span>
            </div>
        </div>`;
}

// ──────────────────────────────────────
// Winner display
// ──────────────────────────────────────

function renderWinner(finalMatches, phase, hideResults) {
    const container = document.getElementById('winner-display');
    if (!container) return;

    if (hideResults || phase !== 'FINISHED' || !finalMatches || finalMatches.length === 0) {
        container.innerHTML = '';
        return;
    }

    // Find the finale (final_round === 1, not loser match)
    const finale = finalMatches.find(m => m.final_round === 1 && !m.is_loser_match && m.status === 'finished');
    if (!finale) {
        container.innerHTML = '';
        return;
    }

    // Determine 1st and 2nd place from the finale
    let first = null, second = null;
    if (finale.score_team1 > finale.score_team2) {
        first = finale.team1;
        second = finale.team2;
    } else if (finale.score_team2 > finale.score_team1) {
        first = finale.team2;
        second = finale.team1;
    }

    if (!first) {
        container.innerHTML = '';
        return;
    }

    // Determine 3rd place from Platz 3 match
    let third = null;
    const platz3 = finalMatches.find(m => m.is_loser_match && m.status === 'finished');
    if (platz3) {
        if (platz3.score_team1 > platz3.score_team2) third = platz3.team1;
        else if (platz3.score_team2 > platz3.score_team1) third = platz3.team2;
    }

    let html = `
        <div class="podium">
            <div class="podium-place podium-1">
                <div class="podium-medal">&#129351;</div>
                ${teamLogo(first, 'xl')}
                <div class="podium-rank">1. Platz</div>
                <div class="podium-name">${esc(first.name)}</div>
                <div class="podium-score">${esc(finale.team1.name)} ${finale.score_team1} : ${finale.score_team2} ${esc(finale.team2.name)}</div>
            </div>
            <div class="podium-place podium-2">
                <div class="podium-medal">&#129352;</div>
                ${teamLogo(second, 'lg')}
                <div class="podium-rank">2. Platz</div>
                <div class="podium-name">${esc(second.name)}</div>
            </div>`;

    if (third) {
        html += `
            <div class="podium-place podium-3">
                <div class="podium-medal">&#129353;</div>
                ${teamLogo(third, 'lg')}
                <div class="podium-rank">3. Platz</div>
                <div class="podium-name">${esc(third.name)}</div>
            </div>`;
    }

    html += `</div>`;
    container.innerHTML = html;
}

// ──────────────────────────────────────
// Local timer (smooth client-side countdown)
// ──────────────────────────────────────

function startLocalTimer() {
    stopLocalTimer();
    localTimerServerSync = Date.now();
    localTimerInterval = setInterval(() => {
        if (!localTimerRunning) { stopLocalTimer(); return; }
        const elapsed = Math.floor((Date.now() - localTimerServerSync) / 1000);
        const remaining = Math.max(0, localTimerRemaining - elapsed);
        const el = document.getElementById('live-timer');
        if (el) {
            el.textContent = formatTime(remaining);
            el.className = 'live-timer';
            if (remaining <= 30) el.classList.add('critical');
            else if (remaining <= 60) el.classList.add('warning');
        }
        renderNextMatchPrep(remaining);
        if (remaining <= 0) stopLocalTimer();
    }, 250);
}

function stopLocalTimer() {
    if (localTimerInterval) {
        clearInterval(localTimerInterval);
        localTimerInterval = null;
    }
}

function updateTimerClass() {
    const el = document.getElementById('live-timer');
    if (!el) return;
    el.className = 'live-timer';
    if (localTimerRemaining <= 30) el.classList.add('critical');
    else if (localTimerRemaining <= 60) el.classList.add('warning');
}

// ──────────────────────────────────────
// Helpers
// ──────────────────────────────────────

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
}

function esc(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

function teamLogo(team, size) {
    if (!team || !team.logo_url) return '';
    const s = size || 'sm';
    return `<img class="team-logo team-logo-${s}" src="${esc(team.logo_url)}" alt="" onerror="this.style.display='none'">`;
}
