// organisation.js – ausgelagert aus templates/admin/organisation.html
// (Nachtschicht 2026-10-24). Die Werte aus der Vorlage
// (SLUG und Co.) setzt ein kurzer Inline-Block davor.
// ── Logo-Vorschau ──
function previewLogo(url) {
    const preview = document.getElementById('logo-preview');
    const img = document.getElementById('logo-img');
    if (url) {
        img.src = url;
        preview.style.display = '';
    } else {
        preview.style.display = 'none';
    }
}

// ── Einstellungen speichern ──
async function saveSettings() {
    const data = {
        entry_fee: document.getElementById('entry_fee').value,
        org_logo_url: document.getElementById('org_logo_url').value,
    };
    const res = await fetch(`/admin/t/${SLUG}/api/org/settings`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
    });
    const d = await res.json();
    const status = document.getElementById('save-status');
    status.textContent = d.ok ? '✓ Gespeichert' : 'Fehler';
    if (d.ok) setTimeout(() => { status.textContent = ''; }, 2500);
}

// ── Toggle bezahlt ──
async function togglePaid(tid, toggleEl) {
    const res = await fetch(`/admin/t/${SLUG}/api/teams/${tid}/toggle-paid`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({}),
    });
    const d = await res.json();
    if (d.error) { alert(d.error); return; }

    const row = toggleEl.closest('.pay-row');
    const statusEl = document.getElementById('status-' + tid);
    const printBtn = document.getElementById('print-btn-' + tid);
    const metaEl = document.getElementById('meta-' + tid);

    toggleEl.classList.toggle('paid', d.paid);
    toggleEl.title = d.paid ? 'Bezahlt – klicken zum Aufheben' : 'Als bezahlt markieren';
    row.dataset.paid = d.paid ? 'paid' : 'unpaid';

    statusEl.textContent = d.paid ? '✓ Bezahlt' : 'Offen';
    statusEl.className = 'pay-status ' + (d.paid ? 'paid' : 'unpaid');

    // Update meta line (keep group name if present)
    const groupPart = metaEl.dataset.group || '';
    metaEl.textContent = d.paid
        ? (groupPart ? groupPart + ' · ' : '') + `Nr. ${d.receipt_number} · ${d.paid_at}`
        : groupPart;

    if (d.paid) {
        printBtn.href = `/admin/t/${SLUG}/organisation/receipt/${tid}`;
        printBtn.classList.remove('disabled');
    } else {
        printBtn.removeAttribute('href');
        printBtn.classList.add('disabled');
    }

    updateSummary();
}

async function markAllPaid() {
    if (!confirm('Alle Teams als bezahlt markieren?')) return;
    const rows = document.querySelectorAll('.pay-row[data-paid="unpaid"]');
    for (const row of rows) {
        const tid = parseInt(row.dataset.id);
        const toggleEl = document.getElementById('toggle-' + tid);
        if (toggleEl) await togglePaid(tid, toggleEl);
    }
}

// ── Summary update ──
function updateSummary() {
    const total = document.querySelectorAll('.pay-row').length;
    const paid = document.querySelectorAll('.pay-row[data-paid="paid"]').length;
    document.getElementById('sum-paid').textContent = paid;
    document.getElementById('sum-unpaid').textContent = total - paid;
}

// ── Checkbox Auswahl ──
function onCheckChange() {
    const checked = document.querySelectorAll('.team-check:checked');
    const count = checked.length;
    const bar = document.getElementById('selection-bar');
    const btnPrint = document.getElementById('btn-print-selected');
    const selLabel = document.getElementById('sel-label');
    const selCount = document.getElementById('sel-count');

    bar.classList.toggle('visible', count > 0);
    btnPrint.style.display = count > 0 ? '' : 'none';
    selLabel.textContent = count + ' ausgewählt';
    if (selCount) selCount.textContent = count;

    // Update "check all" state
    const total = document.querySelectorAll('.team-check').length;
    const checkAll = document.getElementById('check-all');
    if (checkAll) {
        checkAll.indeterminate = count > 0 && count < total;
        checkAll.checked = count === total;
    }
}

function toggleAll(masterCheck) {
    document.querySelectorAll('.team-check').forEach(cb => {
        cb.checked = masterCheck.checked;
    });
    onCheckChange();
}

function selectAll() {
    document.querySelectorAll('.team-check').forEach(cb => cb.checked = true);
    document.getElementById('check-all').checked = true;
    onCheckChange();
}

function selectNone() {
    document.querySelectorAll('.team-check').forEach(cb => cb.checked = false);
    document.getElementById('check-all').checked = false;
    onCheckChange();
}

function printSelected() {
    const ids = Array.from(document.querySelectorAll('.team-check:checked'))
        .map(cb => cb.dataset.id).join(',');
    if (!ids) { alert('Keine Mannschaften ausgewählt.'); return; }
    window.open(`/admin/t/${SLUG}/organisation/receipts/all?ids=${ids}`, '_blank');
}

// Init: store group name in meta element as data attr
document.querySelectorAll('.pay-row').forEach(row => {
    const tid = row.dataset.id;
    const metaEl = document.getElementById('meta-' + tid);
    if (metaEl) {
        // Extract group portion (everything before ' · Nr.')
        const text = metaEl.textContent.trim();
        const nrIdx = text.indexOf(' · Nr.');
        metaEl.dataset.group = nrIdx > -1 ? text.substring(0, nrIdx).trim() : text.split(' · ')[0].trim();
    }
});
