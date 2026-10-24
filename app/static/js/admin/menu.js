// menu.js – ausgelagert aus templates/admin/menu.html
// (Nachtschicht 2026-10-24). Die Werte aus der Vorlage
// Dieses Skript braucht keine Werte aus der Vorlage.
function toggleMenuEdit(id) {
    const row = document.getElementById('menu-edit-' + id);
    row.style.display = row.style.display === 'none' ? '' : 'none';
}

// ── Drag & Drop ──────────────────────────────────────────────
function makeMenuSortable(tbodyId) {
    const el = document.getElementById(tbodyId);
    if (!el) return;
    Sortable.create(el, {
        handle: '.drag-handle',
        animation: 150,
        filter: '.menu-edit-row',
        onEnd() {
            // collect only data rows (skip edit rows)
            const ids = [...el.querySelectorAll('tr[data-id]')].map(r => +r.dataset.id);
            fetch('/admin/api/menu/reorder', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ids})
            }).catch(console.error);
        }
    });
}
makeMenuSortable('sort-speise');
makeMenuSortable('sort-getraenk');

// ── Checkboxes / Bulk delete ─────────────────────────────────
function getCheckedIds() {
    return [...document.querySelectorAll('.item-cb:checked')].map(cb => +cb.value);
}
function onCbChange() {
    const ids = getCheckedIds();
    const toolbar = document.getElementById('bulk-toolbar');
    toolbar.style.display = ids.length ? 'flex' : 'none';
    document.getElementById('bulk-count').textContent = ids.length + ' ausgewaehlt';
}
function selectAll(cat, checked) {
    document.querySelectorAll(`tr[data-cat="${cat}"] .item-cb`).forEach(cb => cb.checked = checked);
    onCbChange();
}
function clearSelection() {
    document.querySelectorAll('.item-cb').forEach(cb => cb.checked = false);
    document.getElementById('sel-all-speise') && (document.getElementById('sel-all-speise').checked = false);
    document.getElementById('sel-all-getraenk') && (document.getElementById('sel-all-getraenk').checked = false);
    onCbChange();
}
function bulkDelete() {
    const ids = getCheckedIds();
    if (!ids.length) return;
    if (!confirm(ids.length + ' Eintraege loeschen?')) return;
    fetch('/admin/api/menu/bulk-delete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ids})
    }).then(r => r.json()).then(d => {
        if (d.ok) location.reload();
        else alert('Fehler: ' + (d.error || 'Unbekannt'));
    }).catch(() => alert('Netzwerkfehler'));
}

// ── CSV Import ────────────────────────────────────────────────
const MENU_IMP_CONFIGS = {
    speisekarte: {
        title: '&#127860; Speisekarte importieren (CSV)',
        hint: 'Format pro Zeile:  Name; Preis; Beschreibung; Kategorie\nKategorie: "speise" oder "getraenk"\nBeispiel:\n  Bratwurst; 3,50 €; mit Senf; speise\n  Cola; 2,00 €; 0,33l; getraenk\nTrenner: Semikolon oder Komma. Beschreibung und Kategorie optional.',
        placeholder: 'Bratwurst; 3,50 €; mit Senf; speise\nPommes; 2,50 €;; speise\nCola; 2,00 €; 0,33l; getraenk',
        url: '/admin/api/menu/import-csv',
        countKey: 'imported',
    },
};
let _menuImpCfg = null;

function openMenuImpModal(type) {
    _menuImpCfg = MENU_IMP_CONFIGS[type];
    document.getElementById('menu-imp-title').innerHTML = _menuImpCfg.title;
    document.getElementById('menu-imp-hint').textContent = _menuImpCfg.hint;
    document.getElementById('menu-imp-ta').value = '';
    document.getElementById('menu-imp-ta').placeholder = _menuImpCfg.placeholder;
    document.getElementById('menu-imp-status').textContent = '';
    document.getElementById('menu-imp-modal').classList.add('open');
    setTimeout(() => document.getElementById('menu-imp-ta').focus(), 80);
}
function closeMenuImpModal() { document.getElementById('menu-imp-modal').classList.remove('open'); }
function menuImpFileLoad(input) {
    const f = input.files[0]; if (!f) return;
    const r = new FileReader();
    r.onload = e => { document.getElementById('menu-imp-ta').value = e.target.result; };
    r.readAsText(f);
}
function runMenuImport() {
    const csv = document.getElementById('menu-imp-ta').value.trim();
    const st = document.getElementById('menu-imp-status');
    if (!csv) { st.textContent = 'Kein CSV-Text eingegeben.'; return; }
    st.textContent = 'Importiere…';
    fetch(_menuImpCfg.url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({csv})
    })
    .then(r => r.json())
    .then(d => {
        if (d.ok) {
            st.textContent = `✓ ${d[_menuImpCfg.countKey]} importiert, ${d.skipped} übersprungen.`;
            setTimeout(() => { closeMenuImpModal(); location.reload(); }, 1200);
        } else {
            st.textContent = 'Fehler: ' + (d.error || 'Unbekannt');
        }
    }).catch(() => { st.textContent = 'Netzwerkfehler'; });
}
