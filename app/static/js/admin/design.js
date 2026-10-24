// design.js – ausgelagert aus templates/admin/design.html
// (Nachtschicht 2026-10-24). Die Werte aus der Vorlage
// (SLUG und Co.) setzt ein kurzer Inline-Block davor.
const DEFAULTS = {
    tournament_name: 'JUGENDFUSSBALLTURNIER',
    color_title:     '#22c55e',
    color_primary:   '#22c55e',
    color_secondary: '#1a2332',
    default_timer_regular: 600,
    default_timer_extra: 300,
};

// Sync color picker <-> hex text input
function linkColorInputs(pickerId, hexId) {
    const picker = document.getElementById(pickerId);
    const hex = document.getElementById(hexId);
    picker.addEventListener('input', () => { hex.value = picker.value; updatePreview(); });
    hex.addEventListener('input', () => {
        if (/^#[0-9a-fA-F]{6}$/.test(hex.value)) {
            picker.value = hex.value;
            updatePreview();
        }
    });
}

linkColorInputs('input-color-title',     'input-color-title-hex');
linkColorInputs('input-color-primary',   'input-color-primary-hex');
linkColorInputs('input-color-secondary', 'input-color-secondary-hex');

document.getElementById('input-name').addEventListener('input', updatePreview);

// Logo URL preview
(function() {
    const logoInput = document.getElementById('input-logo-url');
    const preview = document.getElementById('logo-preview');
    const previewImg = document.getElementById('logo-preview-img');
    function refreshLogoPreview() {
        const url = logoInput.value.trim();
        if (url) { previewImg.src = url; preview.style.display = 'block'; }
        else { preview.style.display = 'none'; }
    }
    logoInput.addEventListener('input', refreshLogoPreview);
    refreshLogoPreview();
})();

function getValues() {
    return {
        theme:           document.getElementById('input-theme').value,
        tournament_name: document.getElementById('input-name').value.trim(),
        color_title:     document.getElementById('input-color-title').value,
        color_primary:   document.getElementById('input-color-primary').value,
        color_secondary: document.getElementById('input-color-secondary').value,
        default_timer_regular: String((parseInt(document.getElementById('input-timer-regular').value) || 10) * 60),
        default_timer_extra:   String((parseInt(document.getElementById('input-timer-extra').value) || 5) * 60),
        hide_table:      document.getElementById('input-hide-table').checked ? '1' : '0',
        hide_scores:     document.getElementById('input-hide-scores').checked ? '1' : '0',
        org_logo_url:    document.getElementById('input-logo-url').value.trim(),
    };
}

function updatePreview() {
    const v = getValues();
    // Header
    document.getElementById('preview-name').textContent = v.tournament_name || 'TURNIER';
    document.getElementById('preview-name').style.color = v.color_title;
    document.getElementById('preview-header').style.borderBottomColor = v.color_primary;
    // Body panels
    document.getElementById('preview-body').style.background = darken(v.color_secondary, 0.4);
    document.getElementById('preview-panel').style.background = v.color_secondary;
    // Accent elements
    document.getElementById('preview-tab').style.background = v.color_primary;
    document.getElementById('preview-tab').style.color = contrastText(v.color_primary);
    document.getElementById('preview-pts').style.color = v.color_primary;
    document.getElementById('preview-badge').style.background = v.color_primary;
    document.getElementById('preview-badge').style.color = contrastText(v.color_primary);
    document.getElementById('preview-score-val').style.color = v.color_primary;
    document.getElementById('preview-live').style.background = v.color_secondary;

    // Also update global CSS custom properties for instant page preview
    document.documentElement.style.setProperty('--color-primary', v.color_primary);
    document.documentElement.style.setProperty('--color-secondary', v.color_secondary);
    document.documentElement.style.setProperty('--color-title', v.color_title);
}

function darken(hex, amount) {
    let r = parseInt(hex.slice(1,3), 16);
    let g = parseInt(hex.slice(3,5), 16);
    let b = parseInt(hex.slice(5,7), 16);
    r = Math.round(r * (1 - amount)); g = Math.round(g * (1 - amount)); b = Math.round(b * (1 - amount));
    return '#' + [r,g,b].map(c => c.toString(16).padStart(2,'0')).join('');
}

function contrastText(hex) {
    const r = parseInt(hex.slice(1,3), 16);
    const g = parseInt(hex.slice(3,5), 16);
    const b = parseInt(hex.slice(5,7), 16);
    return (r*0.299 + g*0.587 + b*0.114) > 150 ? '#000' : '#fff';
}

function setNumFields(val) {
    fetch(`/admin/t/${SLUG}/api/settings`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({num_fields: val})
    }).then(r => r.json()).then(d => {
        if (d.error) { alert('Fehler: ' + d.error); return; }
        for (let n = 1; n <= 6; n++) {
            const btn = document.getElementById('btn-fields-' + n);
            if (btn) btn.className = 'btn btn-sm ' + (val === String(n) ? 'btn-primary' : 'btn-outline');
        }
    });
}

function saveDesign() {
    const data = getValues();
    const status = document.getElementById('save-status');
    status.textContent = 'Speichern...';
    status.className = 'save-status';

    fetch(`/admin/t/${SLUG}/api/settings`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
    })
    .then(r => r.json())
    .then(resp => {
        if (resp.error) {
            status.textContent = 'Fehler: ' + resp.error;
            status.className = 'save-status error';
        } else {
            status.textContent = 'Gespeichert!';
            status.className = 'save-status success';
            setTimeout(() => { status.textContent = ''; }, 3000);
        }
    })
    .catch(() => {
        status.textContent = 'Netzwerkfehler';
        status.className = 'save-status error';
    });
}

function resetDefaults() {
    document.getElementById('input-name').value = DEFAULTS.tournament_name;
    document.getElementById('input-color-title').value = DEFAULTS.color_title;
    document.getElementById('input-color-title-hex').value = DEFAULTS.color_title;
    document.getElementById('input-color-primary').value = DEFAULTS.color_primary;
    document.getElementById('input-color-primary-hex').value = DEFAULTS.color_primary;
    document.getElementById('input-color-secondary').value = DEFAULTS.color_secondary;
    document.getElementById('input-color-secondary-hex').value = DEFAULTS.color_secondary;
    document.getElementById('input-timer-regular').value = DEFAULTS.default_timer_regular / 60;
    document.getElementById('input-timer-extra').value = DEFAULTS.default_timer_extra / 60;
    updatePreview();
}

// Init preview
updatePreview();

// ── Theme swatches ──
function initThemeSwatches() {
    const active = document.getElementById('input-theme').value;
    document.querySelectorAll('.theme-swatch').forEach(btn => {
        btn.classList.toggle('theme-swatch-active', btn.dataset.theme === active);
        btn.addEventListener('click', () => {
            const theme = btn.dataset.theme;
            document.getElementById('input-theme').value = theme;
            // Update color pickers with theme's recommended values
            const primary = btn.dataset.primary;
            const secondary = btn.dataset.secondary;
            const title = btn.dataset.title;
            document.getElementById('input-color-primary').value = primary;
            document.getElementById('input-color-primary-hex').value = primary;
            document.getElementById('input-color-secondary').value = secondary;
            document.getElementById('input-color-secondary-hex').value = secondary;
            document.getElementById('input-color-title').value = title;
            document.getElementById('input-color-title-hex').value = title;
            // Apply theme immediately to page
            document.documentElement.setAttribute('data-theme', theme);
            document.querySelectorAll('.theme-swatch').forEach(b => b.classList.remove('theme-swatch-active'));
            btn.classList.add('theme-swatch-active');
            updatePreview();
        });
    });
}
initThemeSwatches();
