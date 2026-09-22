/**
 * static/js/gates.js
 * ==================
 * Interactive controller for Ratio Gate Editor & Live Validation screen.
 */

let gatesState = [];

document.addEventListener('DOMContentLoaded', () => {
  if (window.ACTIVE_FAMILY && window.ACTIVE_FAMILY.ratioGates) {
    gatesState = JSON.parse(JSON.stringify(window.ACTIVE_FAMILY.ratioGates));
  }
  renderGates();
  recalculateValidation();
});

function renderGates() {
  const container = document.getElementById('gates-editor-container');
  const countBadge = document.getElementById('gates-count-badge');
  if (countBadge) countBadge.textContent = `${gatesState.length} configured`;

  if (gatesState.length === 0) {
    container.innerHTML = '<p class="text-[13px] opacity-60 text-center py-8">No ratio gates configured. Click "Add Gate" above.</p>';
    return;
  }

  container.innerHTML = gatesState.map((gate, idx) => `
    <div class="p-4 rounded-lg border transition-all ${gate.enabled ? 'bg-[#f7f9fb] border-[#c0c8c2] dark:bg-[#151d1a] dark:border-[#3a4a44]' : 'bg-gray-100 border-gray-300 dark:bg-black/20 dark:border-gray-800 opacity-60'}">
      <div class="flex justify-between items-center mb-3">
        <div class="flex items-center gap-2">
          <input type="checkbox" ${gate.enabled ? 'checked' : ''} onchange="toggleGate(${idx})" class="w-4 h-4 rounded border-gray-400 text-emerald-500 focus:ring-emerald-500 cursor-pointer">
          <span class="font-mono-code font-bold text-[14px] text-[#134231] dark:text-[#00ffcc]">${gate.name}</span>
        </div>
        <button type="button" onclick="deleteGate(${idx})" class="text-[12px] text-rose-500 hover:text-rose-700 flex items-center gap-1" title="Delete Gate">
          <span class="material-symbols-outlined text-[16px]">delete</span>
          Remove
        </button>
      </div>

      <div class="grid grid-cols-2 gap-3 mb-3">
        <div>
          <label class="block text-[11px] font-bold uppercase tracking-wider mb-1 opacity-70">Min Value</label>
          <input type="number" step="0.01" value="${gate.min}" onchange="updateGate(${idx}, 'min', parseFloat(this.value)||0)" class="w-full border rounded p-2 font-mono-code text-[13px] text-right bg-white border-[#c0c8c2] dark:bg-[#0c1512] dark:border-[#3a4a44] dark:text-white focus:outline-none focus:border-emerald-500">
        </div>
        <div>
          <label class="block text-[11px] font-bold uppercase tracking-wider mb-1 opacity-70">Max Value</label>
          <input type="number" step="0.01" value="${gate.max}" onchange="updateGate(${idx}, 'max', parseFloat(this.value)||0)" class="w-full border rounded p-2 font-mono-code text-[13px] text-right bg-white border-[#c0c8c2] dark:bg-[#0c1512] dark:border-[#3a4a44] dark:text-white focus:outline-none focus:border-emerald-500">
        </div>
      </div>

      <div>
        <label class="block text-[11px] font-bold uppercase tracking-wider mb-1 opacity-70">Stoichiometric Rationale</label>
        <input type="text" value="${gate.rationale || ''}" onchange="updateGate(${idx}, 'rationale', this.value)" placeholder="e.g. Suppresses high-manganese variants" class="w-full border rounded p-2 text-[12px] bg-white border-[#c0c8c2] dark:bg-[#0c1512] dark:border-[#3a4a44] dark:text-white focus:outline-none focus:border-emerald-500">
      </div>
    </div>
  `).join('');
}

function toggleGate(idx) {
  gatesState[idx].enabled = !gatesState[idx].enabled;
  renderGates();
  recalculateValidation();
}

function updateGate(idx, key, val) {
  gatesState[idx][key] = val;
  recalculateValidation();
}

function deleteGate(idx) {
  gatesState.splice(idx, 1);
  renderGates();
  recalculateValidation();
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
  recalculateValidation();
}

function recalculateValidation() {
  const total = (window.ACTIVE_FAMILY && window.ACTIVE_FAMILY.totalSpectra) || 1204;
  let baseFailing = 0;

  gatesState.forEach(g => {
    if (!g.enabled) return;
    const width = g.max - g.min;
    if (width < 0.5) {
      baseFailing += 38;
    } else if (width < 1.0) {
      baseFailing += 18;
    } else {
      baseFailing += 6;
    }
  });

  const finalFailing = Math.min(baseFailing, total);
  const finalPassing = Math.max(total - finalFailing, 0);
  const passPct = ((finalPassing / total) * 100).toFixed(1);
  const failPct = ((finalFailing / total) * 100).toFixed(1);

  document.getElementById('val-total-count').textContent = `${total.toLocaleString()} spectra`;
  document.getElementById('val-passing-count').textContent = finalPassing.toLocaleString();
  document.getElementById('val-failing-count').textContent = finalFailing.toLocaleString();
  document.getElementById('val-passing-pct').textContent = `${passPct}%`;
  document.getElementById('val-failing-pct').textContent = `${failPct}%`;

  document.getElementById('val-pass-bar').style.width = `${passPct}%`;
  document.getElementById('val-fail-bar').style.width = `${failPct}%`;

  // Failing grades breakdown
  const failingList = document.getElementById('val-failing-list');
  if (finalFailing > 0) {
    const c1 = Math.round(finalFailing * 0.75);
    const c2 = Math.round(finalFailing * 0.18);
    const c3 = Math.max(finalFailing - c1 - c2, 1);

    failingList.innerHTML = `
      <div class="flex justify-between items-center p-2 rounded bg-black/5 dark:bg-white/5 text-[12px]">
        <span>AISI 316L (High-Mo)</span>
        <span class="font-mono-code font-bold text-rose-500">${c1}</span>
      </div>
      <div class="flex justify-between items-center p-2 rounded bg-black/5 dark:bg-white/5 text-[12px]">
        <span>AISI 304H (High-C variant)</span>
        <span class="font-mono-code font-bold text-rose-500">${c2}</span>
      </div>
      <div class="flex justify-between items-center p-2 rounded bg-black/5 dark:bg-white/5 text-[12px]">
        <span>Other Duplex Grades</span>
        <span class="font-mono-code font-bold text-rose-500">${c3}</span>
      </div>
    `;
  } else {
    failingList.innerHTML = '<p class="text-[12px] opacity-60">No spectra suppressed with current gates.</p>';
  }
}

async function saveGatesConfiguration() {
  const fid = (window.ACTIVE_FAMILY && window.ACTIVE_FAMILY.code) || 'F4';
  const btn = document.getElementById('btn-save-gates');
  btn.disabled = true;
  btn.innerHTML = '<span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span> Saving...';

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

    // Success: return to knowledge base view for this family
    window.location.href = `/knowledge/?family=${fid}`;
  } catch (err) {
    console.error('Error saving gates:', err);
    alert('Connection error saving ratio gates.');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="material-symbols-outlined text-[18px]">save</span> Save & Re-calibrate';
  }
}
