// dashboard.js – ausgelagert aus templates/admin/dashboard.html
// (Nachtschicht 2026-10-24). Die Werte aus der Vorlage
// (SLUG und Co.) setzt ein kurzer Inline-Block davor.
// ── UI state persistence ──
const UI_KEY = 'dash_ui_' + SLUG;
function saveUiState() {
    const state = {};
    ['matches','finals'].forEach(n => {
        const el = document.getElementById('sec-' + n);
        if (el) state['sec_' + n] = !el.classList.contains('collapsed');
    });
    sessionStorage.setItem(UI_KEY, JSON.stringify(state));
}
function restoreUiState() {
    const raw = sessionStorage.getItem(UI_KEY);
    if (!raw) return;
    const state = JSON.parse(raw);
    ['matches','finals'].forEach(n => {
        const body  = document.getElementById('sec-' + n);
        const arrow = document.getElementById('arrow-' + n);
        if (!body) return;
        const open = state['sec_' + n];
        if (open === true)  { body.classList.remove('collapsed'); if(arrow) arrow.innerHTML='&#9660;'; }
        if (open === false) { body.classList.add('collapsed');    if(arrow) arrow.innerHTML='&#9654;'; }
    });
}

// ── Section toggle ──
function toggleSection(name) {
    const body  = document.getElementById('sec-' + name);
    const arrow = document.getElementById('arrow-' + name);
    if (!body) return;
    const collapsed = body.classList.toggle('collapsed');
    arrow.innerHTML = collapsed ? '&#9654;' : '&#9660;';
    saveUiState();
}

// ── Sortable ──
function initSortable(id, url) {
    const el = document.getElementById(id);
    if (!el) return;
    Sortable.create(el, {
        handle: '.drag-handle', animation: 150,
        ghostClass: 'sortable-ghost', chosenClass: 'sortable-chosen',
        onEnd: () => {
            const order = Array.from(el.querySelectorAll('.sortable-item')).map(i => parseInt(i.dataset.id));
            fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({order}) });
        },
    });
}
// ── Projected finals (group phase) ──
const PROJ_KEY = 'final_proj_' + SLUG;

function swapProjRow(btn) {
    const tr = btn.closest('tr');
    const t1 = tr.querySelector('.proj-t1');
    const t2 = tr.querySelector('.proj-t2');
    [t1.textContent, t2.textContent] = [t2.textContent, t1.textContent];
    [tr.dataset.team1, tr.dataset.team2] = [tr.dataset.team2, tr.dataset.team1];
    saveProjState();
}

function saveProjState() {
    const tbody = document.getElementById('sortable-proj');
    if (!tbody) return;
    const state = Array.from(tbody.querySelectorAll('tr')).map(tr => ({
        label: tr.dataset.label,
        team1: tr.dataset.team1,
        team2: tr.dataset.team2,
    }));
    localStorage.setItem(PROJ_KEY, JSON.stringify(state));
}

function restoreProjState() {
    const raw = localStorage.getItem(PROJ_KEY);
    if (!raw) return;
    try {
        const state = JSON.parse(raw);
        const tbody = document.getElementById('sortable-proj');
        if (!tbody) return;
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const knownLabels = new Set(rows.map(r => r.dataset.label));
        // Only restore if labels still match (standings may have changed slot set)
        if (!state.every(s => knownLabels.has(s.label))) return;
        state.forEach(s => {
            const row = rows.find(r => r.dataset.label === s.label);
            if (!row) return;
            tbody.appendChild(row);
            row.dataset.team1 = s.team1;
            row.dataset.team2 = s.team2;
            row.querySelector('.proj-t1').textContent = s.team1;
            row.querySelector('.proj-t2').textContent = s.team2;
        });
    } catch(e) {}
}

document.addEventListener('DOMContentLoaded', () => {
    restoreUiState();
    initSortable('sortable-matches', `/admin/t/${SLUG}/api/matches/reorder`);
    initSortable('sortable-finals',  `/admin/t/${SLUG}/api/finals/reorder`);
    const projTbody = document.getElementById('sortable-proj');
    if (projTbody) {
        Sortable.create(projTbody, {
            handle: '.drag-handle', animation: 150,
            ghostClass: 'sortable-ghost', chosenClass: 'sortable-chosen',
            onEnd: saveProjState,
        });
        restoreProjState();
    }
});

// ── Match actions ──
function resetMatchPlanned(mid) {
    fetch(`/admin/t/${SLUG}/api/matches/${mid}/status`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({status:'planned'}) })
        .then(r=>r.json()).then(d=>{ if(d.error) alert(d.error); else location.reload(); });
}
function startFinalMatch(mid) {
    fetch(`/admin/t/${SLUG}/api/matches/${mid}/status`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({status:'live'}) })
        .then(r=>r.json()).then(d=>{ if(d.error) alert(d.error); else location.reload(); });
}
function swapMatchTeams(mid) {
    fetch(`/admin/t/${SLUG}/api/matches/${mid}/swap-teams`, { method:'POST', headers:{'Content-Type':'application/json'}, body:'{}' })
        .then(r=>r.json()).then(d=>{ if(d.error) alert(d.error); else location.reload(); });
}
function startNextMatches() {
    fetch(`/admin/t/${SLUG}/api/matches/start-next`, { method:'POST', headers:{'Content-Type':'application/json'}, body:'{}' })
        .then(r=>r.json()).then(d=>{ if(d.error){alert(d.error);return;} location.reload(); });
}
function toggleField(mid, btn) {
    fetch(`/admin/t/${SLUG}/api/matches/${mid}/set-field`, { method:'POST', headers:{'Content-Type':'application/json'}, body:'{}' })
        .then(r=>r.json()).then(d=>{
            if(d.error){alert(d.error);return;}
            btn.textContent = `F${d.field}`;
            btn.className = btn.className.replace(/badge-(green|yellow)-lt/, d.field===1?'badge-green-lt':'badge-yellow-lt');
        });
}
// ── Phase ──
function phaseApi(url) { return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}).then(r=>r.json()); }
function endGroupStage() { document.getElementById('end-group-modal').classList.add('open'); }
function closeEndGroupModal() { document.getElementById('end-group-modal').classList.remove('open'); }
function pickFinalMode(mode) {
    closeEndGroupModal();
    if (mode === '__keep__') {
        // Keep existing finals as-is — go directly to dashboard, no reordering
        phaseApi(`/admin/t/${SLUG}/api/phase/use-existing-finals`)
            .then(d => { if(d.error) alert(d.error); else location.reload(); });
    } else if (mode === '__none__') {
        // No final round — end tournament directly after group phase
        if (!confirm('Turnier nach der Gruppenphase beenden? Es wird keine Finalrunde geben.')) return;
        phaseApi(`/admin/t/${SLUG}/api/phase/no-finals`)
            .then(d => { if(d.error) alert(d.error); else location.reload(); });
    } else {
        fetch(`/admin/t/${SLUG}/api/settings`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({final_mode: mode})})
            .then(() => phaseApi(`/admin/t/${SLUG}/api/phase/end-group-stage`))
            .then(d => { if(d.error) alert(d.error); else window.location.href = `/admin/t/${SLUG}/finals-setup`; });
    }
}
function finishTournament(){ if(!confirm('Turnier beenden?')) return; phaseApi(`/admin/t/${SLUG}/api/phase/finish-tournament`).then(d=>{if(d.error)alert(d.error);else location.reload();}); }
function resetPhase()      { if(!confirm('Zurücksetzen? Alle Finalspiele werden gelöscht!')) return; phaseApi(`/admin/t/${SLUG}/api/phase/reset`).then(d=>{if(d.error)alert(d.error);else location.reload();}); }


// ── Announcement ──
function saveAnnouncement() {
    const text = document.getElementById('announcement-input').value.trim();
    fetch(`/admin/t/${SLUG}/api/announcement`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({announcement:text})})
        .then(r=>r.json()).then(d=>{ if(d.ok)location.reload(); else alert('Fehler: '+(d.error||'Unbekannt')); })
        .catch(()=>alert('Netzwerkfehler'));
}
function clearAnnouncement() { document.getElementById('announcement-input').value=''; saveAnnouncement(); }
