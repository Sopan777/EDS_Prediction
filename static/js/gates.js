/**
 * static/js/gates.js
 * ==================
 * Interactive controller for Ratio Gate Editor.
 * Manages adding, modifying, and persisting deterministic ratio gates.
 */

let gatesState = [];

document.addEventListener('DOMContentLoaded', () => {
  if (window.ACTIVE_FAMILY && window.ACTIVE_FAMILY.ratioGates) {
    gatesState = JSON.parse(JSON.stringify(window.ACTIVE_FAMILY.ratioGates));
  }
  renderGates();
});

function renderGates() {
  const container = document.getElementById('gates-editor-container');
  const countBadge = document.getElementById('gates-count-badge');
  if (countBadge) countBadge.textContent = `${gatesState.length} configured`;

  if (gatesState.length === 0) {
    container.innerHTML = '<p class="text-xs text-slate-500 text-center py-8">No ratio gates configured for this family. Click "Add Gate" above to establish stoichiometric limits.</p>';
    return;
  }

  container.innerHTML = gatesState.map((gate, idx) => `
    <div class="p-4 rounded border transition-all ${gate.enabled !== false ? 'bg-slate-50 border-slate-200' : 'bg-slate-100 border-slate-200 opacity-60'}">
      <div class="flex justify-between items-center mb-3">
        <div class="flex items-center gap-2">
          <input type="checkbox" ${gate.enabled !== false ? 'checked' : ''} onchange="toggleGate(${idx})" class="w-4 h-4 rounded border-slate-300 text-slate-900 focus:ring-0 cursor-pointer">
          <span class="font-mono-code font-bold text-sm text-slate-900">${gate.name || (gate.numerator + ' / ' + gate.denominator)}</span>
        </div>
        <button type="button" onclick="deleteGate(${idx})" class="text-xs text-rose-600 hover:text-rose-800 flex items-center gap-1 font-semibold" title="Delete Gate">
          <span class="material-symbols-outlined text-[15px]">delete</span>
          Remove
        </button>
      </div>

      <div class="grid grid-cols-2 gap-3 mb-3">
        <div>
          <label class="block text-[11px] font-bold uppercase tracking-wider mb-1 text-slate-600">Min Threshold</label>
          <input type="number" step="0.01" value="${gate.min}" onchange="updateGate(${idx}, 'min', parseFloat(this.value)||0)" class="w-full border border-slate-300 rounded p-2 font-mono-code text-xs text-right bg-white text-slate-900 focus:outline-none focus:border-slate-600">
        </div>
        <div>
          <label class="block text-[11px] font-bold uppercase tracking-wider mb-1 text-slate-600">Max Threshold</label>
          <input type="number" step="0.01" value="${gate.max}" onchange="updateGate(${idx}, 'max', parseFloat(this.value)||0)" class="w-full border border-slate-300 rounded p-2 font-mono-code text-xs text-right bg-white text-slate-900 focus:outline-none focus:border-slate-600">
        </div>
      </div>

      <div>
        <label class="block text-[11px] font-bold uppercase tracking-wider mb-1 text-slate-600">Stoichiometric & Physical Rationale</label>
        <input type="text" value="${gate.rationale || ''}" onchange="updateGate(${idx}, 'rationale', this.value)" placeholder="e.g. Suppresses high-ferrite phases" class="w-full border border-slate-300 rounded p-2 text-xs bg-white text-slate-900 focus:outline-none focus:border-slate-600">
      </div>
    </div>
  `).join('');
}

function toggleGate(idx) {
  gatesState[idx].enabled = !gatesState[idx].enabled;
  renderGates();
}

function updateGate(idx, key, val) {
  gatesState[idx][key] = val;
}

function deleteGate(idx) {
  gatesState.splice(idx, 1);
  renderGates();
}

function openAddGateModal() {
  document.getElementById('add-gate-modal').classList.remove('hidden');
}

function closeAddGateModal() {
  document.getElementById('add-gate-modal').classList.add('hidden');
}

function confirmAddGate(event) {
  event.preventDefault();
  const num = document.getElementById('new-gate-num').value.trim();
  const den = document.getElementById('new-gate-den').value.trim();
  const min = parseFloat(document.getElementById('new-gate-min').value) || 0;
  const max = parseFloat(document.getElementById('new-gate-max').value) || 0;
  const rationale = document.getElementById('new-gate-rationale').value.trim();

  const fid = (window.ACTIVE_FAMILY && window.ACTIVE_FAMILY.code) || 'F4';
  const newGate = {
    id: `gate-${fid.toLowerCase()}-${Date.now()}`,
    name: `${num} / ${den}`,
    numerator: num,
    denominator: den,
    min: min,
    max: max,
    rationale: rationale,
    enabled: true,
  };

  gatesState.push(newGate);
  closeAddGateModal();
  renderGates();
}

async function saveGatesConfiguration() {
  const fid = (window.ACTIVE_FAMILY && window.ACTIVE_FAMILY.code) || 'F4';
  const btn = document.getElementById('btn-save-gates');
  btn.disabled = true;
  btn.innerHTML = '<span class="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span> Saving...';

  try {
    const res = await fetch(`/api/gates/${fid}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({ gates: gatesState }),
    });

    if (!res.ok) {
      alert('Failed to save ratio gates configuration');
      return;
    }

    window.location.href = `/knowledge/?family=${fid}`;
  } catch (err) {
    console.error('Error saving gates:', err);
    alert('Connection error saving ratio gates.');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="material-symbols-outlined text-[16px]">save</span> Save Configuration';
  }
}
