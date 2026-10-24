// export-import.js – ausgelagert aus templates/admin/export_import.html
// (Nachtschicht 2026-10-24). Die Werte aus der Vorlage
// Dieses Skript braucht keine Werte aus der Vorlage.
// ── Export ──
function doExport() {
    const checked = [...document.querySelectorAll('.export-cb:checked')].map(el => el.value);
    const includeMenu = document.getElementById('export-include-menu').checked;
    if (!checked.length && !includeMenu) {
        alert('Bitte mindestens ein Turnier auswaehlen oder die Speisekarte einschliessen.');
        return;
    }
    let url = `/admin/api/export?ids=${checked.join(',')}`;
    if (includeMenu) url += '&include_menu=1';
    window.location.href = url;
}

// ── Import: read file client-side ──
let importFileObject = null;

function readImportFile(input) {
    const file = input.files[0];
    if (!file) return;
    importFileObject = file;

    const reader = new FileReader();
    reader.onload = function(e) {
        const errEl = document.getElementById('import-error');
        errEl.style.display = 'none';
        let data;
        try { data = JSON.parse(e.target.result); }
        catch { errEl.textContent = 'Datei ist kein gueltiges JSON.'; errEl.style.display = 'block'; return; }

        if (!['1', '2'].includes(String(data.version)) || (!Array.isArray(data.tournaments) && !data.menu_items)) {
            errEl.textContent = 'Ungueltiges Exportformat.';
            errEl.style.display = 'block';
            return;
        }

        // Tournaments section
        const tSection = document.getElementById('import-tournaments-section');
        const box = document.getElementById('import-checkboxes');
        box.innerHTML = '';
        if (Array.isArray(data.tournaments) && data.tournaments.length > 0) {
            data.tournaments.forEach(t => {
                const label = document.createElement('label');
                label.className = 'checkbox-label';
                const date = t.event_date ? ` <span class="item-badge badge-date" style="font-size:0.7rem">${t.event_date}</span>` : '';
                label.innerHTML = `<input type="checkbox" class="import-cb" value="${escHtml(t.name)}" checked> ${escHtml(t.name)}${date}`;
                box.appendChild(label);
            });
            tSection.style.display = '';
        } else {
            tSection.style.display = 'none';
        }

        // Menu section
        const mSection = document.getElementById('import-menu-section');
        if (Array.isArray(data.menu_items) && data.menu_items.length > 0) {
            document.getElementById('import-menu-label').textContent =
                `${data.menu_items.length} Speisekarten-Eintraege importieren`;
            mSection.style.display = '';
        } else {
            mSection.style.display = 'none';
        }

        document.getElementById('import-preview').style.display = 'block';
        document.getElementById('import-form').style.display = 'block';
    };
    reader.readAsText(file);
}

function doImport() {
    const selected = [...document.querySelectorAll('.import-cb:checked')].map(el => el.value);
    const includeMenu = document.getElementById('import-include-menu')?.checked;
    if (!selected.length && !includeMenu) {
        alert('Bitte mindestens ein Turnier auswaehlen oder die Speisekarte importieren.');
        return;
    }
    if (!importFileObject) return;

    // Copy file into hidden input via DataTransfer
    const dt = new DataTransfer();
    dt.items.add(importFileObject);
    document.getElementById('import-file-hidden').files = dt.files;

    // Menu flag
    document.getElementById('import-menu-flag').value = includeMenu ? '1' : '0';

    // Build hidden name inputs
    const container = document.getElementById('import-name-inputs');
    container.innerHTML = '';
    selected.forEach(name => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'names';
        input.value = name;
        container.appendChild(input);
    });

    document.getElementById('import-form').submit();
}

// Wire the submit button manually so we can validate first
document.getElementById('import-form').addEventListener('submit', function(e) {
    e.preventDefault();
    doImport();
});

// ── Helpers ──
function toggleAll(cls, checked) {
    document.querySelectorAll('.' + cls).forEach(el => el.checked = checked);
}
function escHtml(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
