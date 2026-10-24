// finals-setup.js – ausgelagert aus templates/admin/finals_setup.html
// (Nachtschicht 2026-10-24). Die Werte aus der Vorlage
// (SLUG und Co.) setzt ein kurzer Inline-Block davor.
let selectedMode = null;

// Vorausgewählten Modus automatisch laden
if (PRESET_MODE) {
    document.addEventListener('DOMContentLoaded', () => selectMode(PRESET_MODE));
}

// ── Custom mode state ──
let customRounds = [];

function selectMode(mode) {
    selectedMode = mode;
    document.querySelectorAll('.mode-card').forEach(c => c.classList.remove('mode-selected'));
    document.querySelector(`[data-mode="${mode}"]`).classList.add('mode-selected');
    renderConfigPanel(mode);
}

function renderConfigPanel(mode) {
    const panel = document.getElementById('config-panel');
    switch(mode) {
        case 'rank_vs_rank': {
            // MAX_RANKS kommt aus dem Inline-Block der Vorlage
            const maxRanks = MAX_RANKS;
            let opts = '';
            for (let i = 1; i <= maxRanks; i++) {
                opts += `<option value="${i}" ${i === maxRanks ? 'selected' : ''}>${i} Platz${i > 1 ? 'ierungen' : ''}</option>`;
            }
            panel.innerHTML = `
                <div class="ctrl-card">
                    <h3 class="ctrl-label">Platzierungsspiele</h3>
                    <p class="empty-hint" style="margin-bottom:0.75rem">Gleicher Rang aus verschiedenen Gruppen spielt gegeneinander.<br>1.A vs 1.B &middot; 2.A vs 2.B &middot; &hellip;</p>
                    <label class="form-label text-muted" style="font-size:0.78rem;font-weight:600">Anzahl Pl&auml;tze ausspielen</label>
                    <select id="cfg-num-ranks" class="design-input">${opts}</select>
                    <button class="btn btn-accent btn-lg" style="margin-top:1rem;width:100%" onclick="startFinals()">
                        Platzierungsspiele starten
                    </button>
                </div>`;
            break;
        }
        case 'classic_ko':
            panel.innerHTML = `
                <div class="ctrl-card">
                    <h3 class="ctrl-label">Startrunde</h3>
                    <select id="cfg-starting-round" class="design-input">
                        <option value="achtelfinale">Achtelfinale (16 Teams)</option>
                        <option value="viertelfinale">Viertelfinale (8 Teams)</option>
                        <option value="halbfinale" selected>Halbfinale (4 Teams)</option>
                    </select>
                    <label class="cfg-checkbox">
                        <input type="checkbox" id="cfg-platz3" checked> Spiel um Platz 3
                    </label>
                    <button class="btn btn-accent btn-lg" style="margin-top:1rem;width:100%" onclick="startFinals()">
                        Finalrunde starten
                    </button>
                </div>`;
            break;
        case 'semi_final':
            panel.innerHTML = `
                <div class="ctrl-card">
                    <h3 class="ctrl-label">Halbfinale + Finale</h3>
                    <p class="empty-hint">4 beste Teams: #1 vs #4, #2 vs #3</p>
                    <label class="cfg-checkbox">
                        <input type="checkbox" id="cfg-platz3" checked> Spiel um Platz 3
                    </label>
                    <button class="btn btn-accent btn-lg" style="margin-top:1rem;width:100%" onclick="startFinals()">
                        Finalrunde starten
                    </button>
                </div>`;
            break;
        case 'direct_final':
            panel.innerHTML = `
                <div class="ctrl-card">
                    <h3 class="ctrl-label">Direktes Finale</h3>
                    <p class="empty-hint">Gesamtrang 1 vs Gesamtrang 2</p>
                    <button class="btn btn-accent btn-lg" style="margin-top:1rem;width:100%" onclick="startFinals()">
                        Finale starten
                    </button>
                </div>`;
            break;
        case 'free_ko':
            panel.innerHTML = `
                <div class="ctrl-card">
                    <h3 class="ctrl-label">Anzahl Teams</h3>
                    <select id="cfg-num-advance" class="design-input">
                        <option value="2">2 Teams</option>
                        <option value="4" selected>4 Teams</option>
                        <option value="8">8 Teams</option>
                        <option value="16">16 Teams</option>
                    </select>
                    <label class="cfg-checkbox">
                        <input type="checkbox" id="cfg-platz3" checked> Spiel um Platz 3
                    </label>
                    <button class="btn btn-accent btn-lg" style="margin-top:1rem;width:100%" onclick="startFinals()">
                        Finalrunde starten
                    </button>
                </div>`;
            break;
        case 'custom':
            if (customRounds.length === 0) {
                customRounds.push({ name: 'Halbfinale', is_loser_round: false, matches: [] });
            }
            renderCustomPanel();
            break;
    }
}

// ──────────────────────────────────────
// Custom mode: rounds, matches, refs, drag & drop
// ──────────────────────────────────────

function escAttr(str) {
    return (str || '').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function getAllMatchLabels() {
    const labels = [];
    customRounds.forEach(r => r.matches.forEach(m => {
        if (m.label) labels.push(m.label);
    }));
    return labels;
}

function buildTeamOptions(currentValue) {
    const labels = getAllMatchLabels();
    let html = '<option value="">-- Waehlen --</option>';
    html += '<optgroup label="Teams">';
    ALL_TEAMS.forEach(t => {
        const val = 'team:' + t.id;
        html += `<option value="${val}" ${currentValue === val ? 'selected' : ''}>${escAttr(t.name)}</option>`;
    });
    html += '</optgroup>';
    if (labels.length > 0) {
        html += '<optgroup label="Aus vorherigem Spiel">';
        labels.forEach(l => {
            const wVal = 'winner:' + l;
            const lVal = 'loser:' + l;
            html += `<option value="${escAttr(wVal)}" ${currentValue === wVal ? 'selected' : ''}>Gewinner: ${escAttr(l)}</option>`;
            html += `<option value="${escAttr(lVal)}" ${currentValue === lVal ? 'selected' : ''}>Verlierer: ${escAttr(l)}</option>`;
        });
        html += '</optgroup>';
    }
    return html;
}

function renderCustomPanel() {
    const panel = document.getElementById('config-panel');

    let roundsHtml = '';
    customRounds.forEach((round, ri) => {
        let matchesHtml = '';
        round.matches.forEach((match, mi) => {
            const t1Val = match.team1_type ? (match.team1_type + ':' + match.team1_value) : '';
            const t2Val = match.team2_type ? (match.team2_type + ':' + match.team2_value) : '';
            matchesHtml += `
                <div class="custom-match-row sortable-item">
                    <span class="drag-handle" title="Ziehen zum Sortieren">&#9776;</span>
                    <input type="text" class="cm-label" value="${escAttr(match.label)}" placeholder="Label">
                    <select class="cm-team1">${buildTeamOptions(t1Val)}</select>
                    <span class="form-vs">vs</span>
                    <select class="cm-team2">${buildTeamOptions(t2Val)}</select>
                    <button class="btn btn-xs btn-danger" onclick="removeCustomMatch(${ri},${mi})">X</button>
                </div>`;
        });

        roundsHtml += `
            <div class="custom-round-card ctrl-card">
                <div class="custom-round-header">
                    <input type="text" class="cr-name design-input" value="${escAttr(round.name)}" placeholder="Rundenname"
                           data-ri="${ri}" onchange="customRounds[${ri}].name=this.value">
                    <label class="cfg-checkbox" style="margin:0;white-space:nowrap">
                        <input type="checkbox" ${round.is_loser_round ? 'checked' : ''}
                               onchange="customRounds[${ri}].is_loser_round=this.checked"> Platz 3
                    </label>
                    <button class="btn btn-xs btn-danger" onclick="removeCustomRound(${ri})">&#10005;</button>
                </div>
                <div class="custom-matches-list" id="cm-list-${ri}">
                    ${matchesHtml || '<p class="empty-hint" style="padding:0.4rem 0">Keine Paarungen</p>'}
                </div>
                <button class="btn btn-xs btn-outline" style="margin-top:0.5rem" onclick="addCustomMatch(${ri})">+ Paarung</button>
            </div>`;
    });

    panel.innerHTML = `
        <div class="ctrl-card" style="text-align:left">
            <h3 class="ctrl-label">Eigene Paarungen</h3>
            <div id="custom-rounds-container">${roundsHtml}</div>
            <div style="display:flex;gap:0.5rem;margin-top:0.75rem">
                <button class="btn btn-sm btn-outline" onclick="addCustomRound()">+ Runde hinzufuegen</button>
                <button class="btn btn-sm btn-outline" onclick="refreshCustomRefs()">Referenzen aktualisieren</button>
            </div>
            <button class="btn btn-accent btn-lg" style="margin-top:1rem;width:100%" onclick="startFinals()">
                Finalrunde starten
            </button>
        </div>`;

    initCustomSortable();
}

function initCustomSortable() {
    customRounds.forEach((r, ri) => {
        const el = document.getElementById('cm-list-' + ri);
        if (el) {
            Sortable.create(el, {
                handle: '.drag-handle',
                group: 'custom-matches',
                animation: 200,
                ghostClass: 'sortable-ghost',
                chosenClass: 'sortable-chosen',
                onEnd: syncCustomFromDOM,
            });
        }
    });
}

function syncCustomFromDOM() {
    customRounds.forEach((round, ri) => {
        const container = document.getElementById('cm-list-' + ri);
        if (!container) { round.matches = []; return; }
        const rows = container.querySelectorAll('.custom-match-row');
        round.matches = Array.from(rows).map(row => {
            const label = row.querySelector('.cm-label').value;
            const t1Raw = row.querySelector('.cm-team1').value;
            const t2Raw = row.querySelector('.cm-team2').value;
            return {
                label: label,
                team1_type: t1Raw ? t1Raw.split(':')[0] : '',
                team1_value: t1Raw ? t1Raw.substring(t1Raw.indexOf(':') + 1) : '',
                team2_type: t2Raw ? t2Raw.split(':')[0] : '',
                team2_value: t2Raw ? t2Raw.substring(t2Raw.indexOf(':') + 1) : '',
            };
        });
    });
    renderCustomPanel();
}

function saveCustomInputs() {
    customRounds.forEach((round, ri) => {
        const container = document.getElementById('cm-list-' + ri);
        if (!container) return;
        const rows = container.querySelectorAll('.custom-match-row');
        rows.forEach((row, mi) => {
            if (mi >= round.matches.length) return;
            const m = round.matches[mi];
            m.label = row.querySelector('.cm-label').value;
            const t1Raw = row.querySelector('.cm-team1').value;
            const t2Raw = row.querySelector('.cm-team2').value;
            m.team1_type = t1Raw ? t1Raw.split(':')[0] : '';
            m.team1_value = t1Raw ? t1Raw.substring(t1Raw.indexOf(':') + 1) : '';
            m.team2_type = t2Raw ? t2Raw.split(':')[0] : '';
            m.team2_value = t2Raw ? t2Raw.substring(t2Raw.indexOf(':') + 1) : '';
        });
        const nameInput = document.querySelector(`.cr-name[data-ri="${ri}"]`);
        if (nameInput) round.name = nameInput.value;
    });
}

function addCustomRound() {
    saveCustomInputs();
    customRounds.push({ name: 'Runde ' + (customRounds.length + 1), is_loser_round: false, matches: [] });
    renderCustomPanel();
}

function removeCustomRound(ri) {
    saveCustomInputs();
    if (!confirm('Runde "' + customRounds[ri].name + '" loeschen?')) return;
    customRounds.splice(ri, 1);
    renderCustomPanel();
}

function addCustomMatch(ri) {
    saveCustomInputs();
    const round = customRounds[ri];
    round.matches.push({
        label: round.name + ' ' + (round.matches.length + 1),
        team1_type: '', team1_value: '',
        team2_type: '', team2_value: '',
    });
    renderCustomPanel();
}

function removeCustomMatch(ri, mi) {
    saveCustomInputs();
    customRounds[ri].matches.splice(mi, 1);
    renderCustomPanel();
}

function refreshCustomRefs() {
    saveCustomInputs();
    renderCustomPanel();
}

// ──────────────────────────────────────
// Start finals
// ──────────────────────────────────────

function startFinals() {
    let config = {};
    switch(selectedMode) {
        case 'classic_ko':
            config = {
                starting_round: document.getElementById('cfg-starting-round').value,
                platz3: document.getElementById('cfg-platz3').checked,
            };
            break;
        case 'semi_final':
            config = { platz3: document.getElementById('cfg-platz3').checked };
            break;
        case 'rank_vs_rank':
            config = { num_ranks: parseInt(document.getElementById('cfg-num-ranks').value) };
            break;
        case 'direct_final':
            config = {};
            break;
        case 'free_ko':
            config = {
                num_advance: parseInt(document.getElementById('cfg-num-advance').value),
                platz3: document.getElementById('cfg-platz3').checked,
            };
            break;
        case 'custom':
            saveCustomInputs();
            config = {
                rounds: customRounds.map(r => ({
                    name: r.name,
                    is_loser_round: r.is_loser_round,
                    matches: r.matches.map(m => ({
                        label: m.label,
                        team1_type: m.team1_type,
                        team1_value: m.team1_value,
                        team2_type: m.team2_type,
                        team2_value: m.team2_value,
                    }))
                }))
            };
            break;
    }

    if (!selectedMode) { alert('Bitte Modus waehlen'); return; }

    fetch(`/admin/t/${SLUG}/api/phase/start-final-round`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ mode: selectedMode, config }),
    })
    .then(r => r.json())
    .then(d => {
        if (d.error) { alert(d.error); return; }
        window.location.href = `/admin/t/${SLUG}/`;
    })
    .catch(() => alert('Netzwerkfehler'));
}
