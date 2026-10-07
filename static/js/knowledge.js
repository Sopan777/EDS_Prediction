/**
 * static/js/knowledge.js
 * ======================
 * Controller for DHATU BODH Knowledge Base screen (/knowledge/).
 * Handles:
 *  - 5-Tab switching (Direct Families, Indirect Sources KB, Components, Spectra, Ratio Gates)
 *  - Universal search across all 5 tabs
 *  - Instant client-side Direct Family & Indirect Family selection
 *  - Full interactive customization modals for:
 *      1. Direct Material Families (Name, Grade Hint, Status, Note, Discriminators, Element Bands, Components)
 *      2. Indirect Material Families & Cleaning-Area Parts (with live ±25%/±20%/±10% tolerance calculation)
 *      3. Canonical Component Fingerprints (Display Name, Material Body, Family IDs, Aliases, Element Medians/IQR)
 */

let activeKbTab = 'families';
let activeIndirectFamilyFilter = 'ALL';

function switchKbTab(tab) {
  activeKbTab = tab;

  const tabs = ['families', 'indirect', 'components', 'spectra', 'gates'];
  const activeClass = 'px-3 py-1.5 rounded-md bg-white text-slate-900 shadow-xs transition-all font-bold';
  const inactiveClass = 'px-3 py-1.5 rounded-md text-slate-600 hover:text-slate-900 transition-all font-medium';

  tabs.forEach(t => {
    const viewEl = document.getElementById(`kb-view-${t}`);
    const btnEl = document.getElementById(`tab-btn-${t}`);
    if (viewEl) viewEl.classList.toggle('hidden', t !== tab);
    if (btnEl) btnEl.className = t === tab ? activeClass : inactiveClass;
  });

  const searchInput = document.getElementById('kb-search-input');
  if (searchInput && searchInput.value) {
    handleKbSearch(searchInput.value);
  }
}
window.switchKbTab = switchKbTab;

function handleKbSearch(query) {
  const q = (query || '').toLowerCase().trim();

  if (activeKbTab === 'families') {
    document.querySelectorAll('.family-item').forEach(item => {
      const code = (item.getAttribute('data-code') || '').toLowerCase();
      const name = (item.getAttribute('data-name') || '').toLowerCase();
      const desc = (item.getAttribute('data-desc') || '').toLowerCase();
      item.classList.toggle('hidden', Boolean(q && !code.includes(q) && !name.includes(q) && !desc.includes(q)));
    });
  } else if (activeKbTab === 'indirect') {
    document.querySelectorAll('.indirect-part-row').forEach(row => {
      const name = (row.getAttribute('data-name') || '').toLowerCase();
      const mat = (row.getAttribute('data-mat') || '');
      const loc = (row.getAttribute('data-loc') || '').toLowerCase();
      const text = (row.textContent || '').toLowerCase();
      const matchesFam = activeIndirectFamilyFilter === 'ALL' || mat === activeIndirectFamilyFilter;
      const matchesQuery = !q || name.includes(q) || mat.toLowerCase().includes(q) || loc.includes(q) || text.includes(q);
      row.classList.toggle('hidden', !(matchesFam && matchesQuery));
    });
  } else if (activeKbTab === 'components') {
    document.querySelectorAll('.component-row').forEach(row => {
      const name = (row.getAttribute('data-name') || '').toLowerCase();
      const id = (row.getAttribute('data-id') || '').toLowerCase();
      const mat = (row.getAttribute('data-mat') || '').toLowerCase();
      const aliases = (row.getAttribute('data-aliases') || '').toLowerCase();
      row.classList.toggle('hidden', Boolean(q && !name.includes(q) && !id.includes(q) && !mat.includes(q) && !aliases.includes(q)));
    });
  } else if (activeKbTab === 'spectra') {
    document.querySelectorAll('.spectrum-row').forEach(row => {
      const id = (row.getAttribute('data-id') || '').toLowerCase();
      const comp = (row.getAttribute('data-comp') || '').toLowerCase();
      const summary = (row.getAttribute('data-summary') || '').toLowerCase();
      row.classList.toggle('hidden', Boolean(q && !id.includes(q) && !comp.includes(q) && !summary.includes(q)));
    });
  } else if (activeKbTab === 'gates') {
    document.querySelectorAll('.gate-row').forEach(row => {
      const fam = (row.getAttribute('data-fam') || '').toLowerCase();
      const code = (row.getAttribute('data-code') || '').toLowerCase();
      const name = (row.getAttribute('data-name') || '').toLowerCase();
      row.classList.toggle('hidden', Boolean(q && !fam.includes(q) && !code.includes(q) && !name.includes(q)));
    });
  }
}
window.handleKbSearch = handleKbSearch;

// ============================================================================
// 1. DIRECT MATERIAL FAMILIES SELECTION & RENDERING
// ============================================================================
function selectFamily(code) {
  if (!window.KB_FAMILIES) {
    window.location.href = `/knowledge/?family=${encodeURIComponent(code)}`;
    return;
  }
  const family = window.KB_FAMILIES.find(f => f.code === code);
  if (!family) return;

  window.ACTIVE_FAMILY = family;

  const url = new URL(window.location);
  url.searchParams.set('family', code);
  window.history.pushState({}, '', url);

  // Update left sidebar active highlights
  document.querySelectorAll('.family-item').forEach(item => {
    const itemCode = item.getAttribute('data-code');
    if (itemCode === code) {
      item.className = 'family-item p-3 rounded-lg border cursor-pointer transition-all border-[#ED0007] bg-[#FFF1F2] border-l-4 border-l-[#ED0007]';
    } else {
      item.className = 'family-item p-3 rounded-lg border cursor-pointer transition-all border-slate-200 hover:border-slate-300 bg-white';
    }
  });

  // Update right column details
  const codePill = document.getElementById('detail-code-pill');
  const statusPill = document.getElementById('detail-status-pill');
  const spectraPill = document.getElementById('detail-spectra-pill');
  const famName = document.getElementById('detail-family-name');
  const gradeHint = document.getElementById('detail-grade-hint');
  const descEl = document.getElementById('detail-description');
  const discList = document.getElementById('detail-discriminators-list');
  const btnEditGates = document.getElementById('btn-edit-profile');
  const linkCalibrate = document.getElementById('link-calibrate-gates');

  if (codePill) codePill.textContent = family.code;
  if (statusPill) {
    statusPill.textContent = `${family.status} SPECIFICATION`;
    statusPill.className = family.status === 'FIRM'
      ? 'px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800'
      : 'px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-amber-100 text-amber-800';
  }
  if (spectraPill) spectraPill.textContent = `${family.nSpectra || 5} Reference Spectra`;
  if (famName) famName.textContent = family.name;
  if (gradeHint) gradeHint.textContent = `Grade hint: ${family.gradeHint || 'Standard Reference'}`;
  if (descEl) descEl.textContent = family.description || '';
  if (btnEditGates) btnEditGates.setAttribute('href', `/gates/${family.code}/`);
  if (linkCalibrate) linkCalibrate.setAttribute('href', `/gates/${family.code}/`);

  if (discList) {
    const discs = family.discriminators || [];
    discList.innerHTML = discs.length
      ? discs.map(d => `<span class="px-2 py-0.5 rounded text-[11px] font-mono-code font-bold bg-blue-50 text-blue-800 border border-blue-200">${escapeHtml(d)}</span>`).join('')
      : '<span class="text-xs text-slate-400">Standard band profile</span>';
  }

  // Element Bands Table
  const tbody = document.getElementById('bands-table-body');
  const bands = family.elementBands || [];
  if (tbody) {
    if (bands.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="py-4 text-center text-slate-500 font-sans">No concentration bands mapped.</td></tr>';
    } else {
      tbody.innerHTML = bands.map(band => {
        const minVal = Number(band.rangeMin ?? band.min_wt_pct ?? 0).toFixed(2);
        const maxVal = Number(band.rangeMax ?? band.max_wt_pct ?? 0).toFixed(2);
        const meanVal = Number(band.meanWt ?? band.mean_wt_pct ?? ((Number(minVal) + Number(maxVal)) / 2)).toFixed(2);
        const roleBadge = band.role === 'Required'
          ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-100 text-emerald-800">Required</span>'
          : band.role === 'Trace'
          ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-100 text-amber-800">Trace</span>'
          : '<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-100 text-slate-700">Allowed</span>';
        const discBadge = band.isDiscriminator
          ? '<span class="ml-1 px-1.5 py-0.2 rounded text-[9px] font-sans font-bold bg-blue-50 text-blue-700 border border-blue-200" title="Primary Family Discriminator">DISC</span>'
          : '';
        return `
          <tr class="hover:bg-slate-50 transition-colors">
            <td class="py-2.5 px-4 font-bold text-slate-900">${escapeHtml(band.element)}${discBadge}</td>
            <td class="py-2.5 px-4 font-sans">${roleBadge}</td>
            <td class="py-2.5 px-4 text-right">${minVal}%</td>
            <td class="py-2.5 px-4 text-right">${maxVal}%</td>
            <td class="py-2.5 px-4 text-right text-slate-500">${meanVal}%</td>
            <td class="py-2.5 px-4">
              <div class="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                <div class="bg-[#ED0007] h-full rounded-full" style="width: ${band.barWidthPct || 65}%"></div>
              </div>
            </td>
          </tr>
        `;
      }).join('');
    }
  }

  // Associated Components Grid
  const compGrid = document.getElementById('family-components-grid');
  const compCount = document.getElementById('family-components-count');
  const comps = family.components || (family.candidateComponents || []).map(c => c.name);
  if (compCount) compCount.textContent = `${comps.length} parts`;
  if (compGrid) {
    if (comps.length === 0) {
      compGrid.innerHTML = '<div class="col-span-3 p-4 text-center text-slate-500">No components explicitly mapped to this family. Click "Add / Edit Components" to assign parts.</div>';
    } else {
      compGrid.innerHTML = comps.map(c => `
        <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between gap-2">
          <span class="font-semibold text-slate-800 truncate">${escapeHtml(c)}</span>
          <span class="text-[10px] font-mono-code text-slate-500 bg-white px-1.5 py-0.5 rounded border border-slate-200 shrink-0">
            ${escapeHtml(family.code)}
          </span>
        </div>
      `).join('');
    }
  }

  // Ratio Gates List
  const gatesList = document.getElementById('family-ratio-gates-list');
  const gates = family.ratioGates || [];
  if (gatesList) {
    if (gates.length === 0) {
      gatesList.innerHTML = '<div class="p-4 bg-slate-50 rounded-lg text-xs text-slate-500 text-center">No specific stoichiometric ratio gates enforced for this family. Classification relies on elemental concentration bands.</div>';
    } else {
      gatesList.innerHTML = gates.map(gate => `
        <div class="p-4 bg-slate-50 border border-slate-200 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div>
            <div class="font-bold text-slate-900 text-sm">${escapeHtml(gate.name)}</div>
            <div class="text-slate-500 font-mono-code mt-0.5">
              Formula: <strong>${escapeHtml(gate.numerator)} / ${escapeHtml(gate.denominator)}</strong> &bull; Allowed Band: <strong>${gate.min} – ${gate.max}</strong>
            </div>
            <div class="text-slate-600 mt-2">${escapeHtml(gate.rationale || '')}</div>
          </div>
          <span class="px-2.5 py-1 rounded text-xs font-bold uppercase bg-emerald-100 text-emerald-800 shrink-0">
            ACTIVE GATE
          </span>
        </div>
      `).join('');
    }
  }
}
window.selectFamily = selectFamily;

// ============================================================================
// 2. INDIRECT SOURCES KB FILTERING & TOLERANCE HELPER
// ============================================================================
function computeIndirectTolerancePreview(val) {
  const num = parseFloat(val);
  if (isNaN(num) || num <= 0) return { tolLabel: '—', min: '—', max: '—' };
  let tol = 0.10;
  if (num < 1.0) tol = 0.25;
  else if (num <= 5.0) tol = 0.20;
  const minV = (num * (1 - tol)).toFixed(3);
  const maxV = (num * (1 + tol)).toFixed(3);
  return { tolLabel: `±${Math.round(tol * 100)}%`, min: minV, max: maxV };
}

function filterIndirectByFamily(famName) {
  activeIndirectFamilyFilter = famName;

  const allBtn = document.getElementById('indirect-fam-btn-ALL');
  if (allBtn) {
    allBtn.className = famName === 'ALL'
      ? 'w-full text-left p-3 rounded-lg border border-[#ED0007] bg-[#FFF1F2] border-l-4 border-l-[#ED0007] transition-all flex items-center justify-between'
      : 'w-full text-left p-3 rounded-lg border border-slate-200 hover:border-slate-300 bg-white transition-all flex items-center justify-between';
  }

  document.querySelectorAll('.indirect-family-card').forEach(card => {
    const cardFam = card.getAttribute('data-ifam');
    if (cardFam === famName) {
      card.className = 'indirect-family-card p-3 rounded-lg border border-[#ED0007] bg-[#FFF1F2] border-l-4 border-l-[#ED0007] cursor-pointer transition-all space-y-2';
    } else {
      card.className = 'indirect-family-card p-3 rounded-lg border border-slate-200 hover:border-slate-300 bg-white cursor-pointer transition-all space-y-2';
    }
  });

  let visibleCount = 0;
  document.querySelectorAll('.indirect-part-row').forEach(row => {
    const rowMat = row.getAttribute('data-mat');
    const show = famName === 'ALL' || rowMat === famName;
    row.classList.toggle('hidden', !show);
    if (show) visibleCount++;
  });

  const heading = document.getElementById('indirect-parts-heading');
  if (heading) {
    heading.textContent = famName === 'ALL'
      ? `All Indirect Material Sources (${visibleCount} Parts)`
      : `Indirect Sources in Family "${famName}" (${visibleCount} Parts)`;
  }
}
window.filterIndirectByFamily = filterIndirectByFamily;

// ============================================================================
// 3. MODAL WORKBENCH CONTROLLER
// ============================================================================
function openKbCustomizeModal({ title, subtitle, bodyHtml, leftActionsHtml = '', onSave }) {
  document.getElementById('kb-customize-title').textContent = title;
  document.getElementById('kb-customize-subtitle').textContent = subtitle || '';
  document.getElementById('kb-customize-body').innerHTML = bodyHtml;
  document.getElementById('kb-customize-left-actions').innerHTML = leftActionsHtml;

  const saveBtn = document.getElementById('kb-customize-save-btn');
  saveBtn.disabled = false;
  saveBtn.innerHTML = '<span class="material-symbols-outlined text-[16px]">save</span><span>Save Changes</span>';
  saveBtn.onclick = onSave;

  document.getElementById('kb-customize-modal').classList.remove('hidden');
}

function closeKbCustomizeModal() {
  document.getElementById('kb-customize-modal').classList.add('hidden');
}
window.closeKbCustomizeModal = closeKbCustomizeModal;

function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ============================================================================
// 4. CUSTOMIZE DIRECT MATERIAL FAMILY (NAME, GRADE HINT, BANDS, COMPONENTS)
// ============================================================================
function openCustomizeFamilyModal(isNew = false) {
  const fam = isNew
    ? {
        code: '',
        name: '',
        gradeHint: '',
        status: 'FIRM',
        description: '',
        discriminators: ['Fe', 'Cr'],
        elementBands: [
          { element: 'Fe', role: 'Required', rangeMin: 70.0, rangeMax: 99.0, meanWt: 85.0 },
          { element: 'Cr', role: 'Required', rangeMin: 1.0, rangeMax: 20.0, meanWt: 12.0 },
        ],
        components: [],
      }
    : (window.ACTIVE_FAMILY || {});

  const bandsRowsHtml = (fam.elementBands || []).map((b, idx) => renderFamilyBandEditorRow(b, idx)).join('');
  const compsText = (fam.components || []).join(', ');
  const discsText = (fam.discriminators || []).join(', ');

  const bodyHtml = `
    <div class="grid grid-cols-1 sm:grid-cols-12 gap-4">
      <div class="sm:col-span-3">
        <label class="block font-bold text-slate-700 mb-1">Family Code</label>
        <input type="text" id="cust-fam-code" value="${escapeHtml(fam.code)}" ${isNew ? '' : 'readonly'} placeholder="e.g. F9" class="w-full border border-slate-300 rounded-lg p-2 font-mono-code font-bold text-slate-900 ${isNew ? 'bg-white' : 'bg-slate-100'}">
      </div>
      <div class="sm:col-span-6">
        <label class="block font-bold text-slate-700 mb-1">Material Family Name</label>
        <input type="text" id="cust-fam-name" value="${escapeHtml(fam.name)}" placeholder="e.g. Austenitic stainless steel (Cr-Ni)" class="w-full border border-slate-300 rounded-lg p-2 font-semibold text-slate-900 bg-white">
      </div>
      <div class="sm:col-span-3">
        <label class="block font-bold text-slate-700 mb-1">Specification Status</label>
        <select id="cust-fam-status" class="w-full border border-slate-300 rounded-lg p-2 font-bold text-slate-900 bg-white">
          <option value="FIRM" ${fam.status === 'FIRM' ? 'selected' : ''}>FIRM</option>
          <option value="PROV" ${fam.status !== 'FIRM' ? 'selected' : ''}>PROV (Provisional)</option>
        </select>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div>
        <label class="block font-bold text-slate-700 mb-1">International Grade Hint</label>
        <input type="text" id="cust-fam-grade" value="${escapeHtml(fam.gradeHint)}" placeholder="e.g. AISI 303 / 304, X8CrNiS18-9" class="w-full border border-slate-300 rounded-lg p-2 text-slate-900 bg-white">
      </div>
      <div>
        <label class="block font-bold text-slate-700 mb-1">Key Discriminator Elements / Ratios (comma-separated)</label>
        <input type="text" id="cust-fam-discs" value="${escapeHtml(discsText)}" placeholder="e.g. Cr, Ni" class="w-full border border-slate-300 rounded-lg p-2 font-mono-code text-slate-900 bg-white">
      </div>
    </div>

    <div>
      <label class="block font-bold text-slate-700 mb-1">Metallurgical Description &amp; Notes</label>
      <textarea id="cust-fam-desc" rows="2" class="w-full border border-slate-300 rounded-lg p-2 text-slate-900 bg-white">${escapeHtml(fam.description)}</textarea>
    </div>

    <div>
      <label class="block font-bold text-slate-700 mb-1">Associated Components (comma-separated part names)</label>
      <textarea id="cust-fam-comps" rows="2" placeholder="e.g. Adjustment Screw, Filter Ring, Magnet Cup" class="w-full border border-slate-300 rounded-lg p-2 text-slate-900 bg-white">${escapeHtml(compsText)}</textarea>
      <p class="text-[11px] text-slate-500 mt-1">All listed components will be mapped to this material family during Direct Component prediction.</p>
    </div>

    <div class="space-y-2">
      <div class="flex items-center justify-between">
        <label class="font-bold text-slate-700 uppercase tracking-wider text-[11px]">Elemental Concentration Bands (Metal-Basis wt%)</label>
        <button type="button" onclick="addFamilyBandEditorRow()" class="px-2.5 py-1 rounded border border-slate-300 bg-white hover:bg-slate-50 font-semibold text-slate-700 flex items-center gap-1">
          <span class="material-symbols-outlined text-[14px]">add</span>
          <span>Add Element Band</span>
        </button>
      </div>
      <div class="border border-slate-200 rounded-lg overflow-hidden">
        <table class="w-full text-left border-collapse text-xs">
          <thead class="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase text-[10px]">
            <tr>
              <th class="py-2 px-3">Element</th>
              <th class="py-2 px-3">Role</th>
              <th class="py-2 px-3 text-right">Min wt%</th>
              <th class="py-2 px-3 text-right">Max wt%</th>
              <th class="py-2 px-3 text-right">Mean wt%</th>
              <th class="py-2 px-3 text-center w-12"></th>
            </tr>
          </thead>
          <tbody id="cust-fam-bands-tbody" class="divide-y divide-slate-100">
            ${bandsRowsHtml}
          </tbody>
        </table>
      </div>
    </div>
  `;

  openKbCustomizeModal({
    title: isNew ? 'Create New Direct Material Family' : `Customize Material Family: ${fam.code} — ${fam.name}`,
    subtitle: 'Modify family name, grade hint, associated components, or elemental concentration bands.',
    bodyHtml,
    onSave: () => submitCustomizeFamily(isNew),
  });
}
window.openCustomizeFamilyModal = openCustomizeFamilyModal;

function renderFamilyBandEditorRow(b = {}, idx = 0) {
  const el = b.element || '';
  const role = b.role || 'Allowed';
  const minV = Number(b.rangeMin ?? b.min_wt_pct ?? 0);
  const maxV = Number(b.rangeMax ?? b.max_wt_pct ?? 10);
  const meanV = Number(b.meanWt ?? b.mean_wt_pct ?? ((minV + maxV) / 2));

  return `
    <tr class="cust-fam-band-row">
      <td class="p-2">
        <input type="text" class="band-el w-20 border border-slate-300 rounded p-1.5 font-mono-code font-bold text-slate-900 bg-white" value="${escapeHtml(el)}" placeholder="Cr">
      </td>
      <td class="p-2">
        <select class="band-role border border-slate-300 rounded p-1.5 text-slate-900 bg-white">
          <option value="Required" ${role === 'Required' ? 'selected' : ''}>Required</option>
          <option value="Allowed" ${role === 'Allowed' || role === 'Optional' ? 'selected' : ''}>Allowed</option>
          <option value="Trace" ${role === 'Trace' ? 'selected' : ''}>Trace</option>
        </select>
      </td>
      <td class="p-2">
        <input type="number" step="0.01" class="band-min w-24 border border-slate-300 rounded p-1.5 text-right font-mono-code text-slate-900 bg-white" value="${minV}">
      </td>
      <td class="p-2">
        <input type="number" step="0.01" class="band-max w-24 border border-slate-300 rounded p-1.5 text-right font-mono-code text-slate-900 bg-white" value="${maxV}">
      </td>
      <td class="p-2">
        <input type="number" step="0.01" class="band-mean w-24 border border-slate-300 rounded p-1.5 text-right font-mono-code text-slate-900 bg-white" value="${meanV}">
      </td>
      <td class="p-2 text-center">
        <button type="button" onclick="this.closest('tr').remove()" class="text-rose-600 hover:text-rose-800 p-1" title="Remove Element">
          <span class="material-symbols-outlined text-[16px]">delete</span>
        </button>
      </td>
    </tr>
  `;
}

function addFamilyBandEditorRow() {
  const tbody = document.getElementById('cust-fam-bands-tbody');
  if (!tbody) return;
  tbody.insertAdjacentHTML('beforeend', renderFamilyBandEditorRow({ element: '', role: 'Allowed', rangeMin: 0.0, rangeMax: 5.0, meanWt: 1.0 }));
}
window.addFamilyBandEditorRow = addFamilyBandEditorRow;

async function submitCustomizeFamily(isNew) {
  const code = document.getElementById('cust-fam-code').value.trim();
  const name = document.getElementById('cust-fam-name').value.trim();
  const status = document.getElementById('cust-fam-status').value;
  const gradeHint = document.getElementById('cust-fam-grade').value.trim();
  const description = document.getElementById('cust-fam-desc').value.trim();
  const discsRaw = document.getElementById('cust-fam-discs').value;
  const compsRaw = document.getElementById('cust-fam-comps').value;

  if (!code || !name) {
    alert('Family Code and Material Family Name are required.');
    return;
  }

  const elementBands = [];
  document.querySelectorAll('#cust-fam-bands-tbody .cust-fam-band-row').forEach(tr => {
    const el = tr.querySelector('.band-el').value.trim();
    const role = tr.querySelector('.band-role').value;
    const minVal = parseFloat(tr.querySelector('.band-min').value) || 0;
    const maxVal = parseFloat(tr.querySelector('.band-max').value) || 0;
    const meanVal = parseFloat(tr.querySelector('.band-mean').value) || ((minVal + maxVal) / 2);
    if (el) {
      elementBands.push({
        element: el,
        role,
        rangeMin: minVal,
        rangeMax: maxVal,
        meanWt: meanVal,
      });
    }
  });

  if (elementBands.length === 0) {
    alert('Please configure at least one Elemental Concentration Band.');
    return;
  }

  const discriminators = discsRaw.split(',').map(s => s.trim()).filter(Boolean);
  const components = compsRaw.split(',').map(s => s.trim()).filter(Boolean);

  const saveBtn = document.getElementById('kb-customize-save-btn');
  saveBtn.disabled = true;
  saveBtn.innerHTML = 'Saving...';

  try {
    const endpoint = isNew ? '/api/families' : `/api/families/${encodeURIComponent(code)}`;
    const res = await fetch(endpoint, {
      method: isNew ? 'POST' : 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': typeof getCSRFToken === 'function' ? getCSRFToken() : '',
      },
      body: JSON.stringify({
        code,
        name,
        status,
        gradeHint,
        description,
        discriminators,
        components,
        elementBands,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.error || 'Failed to save family customization.');
      saveBtn.disabled = false;
      saveBtn.innerHTML = '<span class="material-symbols-outlined text-[16px]">save</span><span>Save Changes</span>';
      return;
    }

    closeKbCustomizeModal();
    window.location.href = `/knowledge/?family=${encodeURIComponent(code)}`;
  } catch (err) {
    alert('Network error saving family customization.');
    saveBtn.disabled = false;
  }
}

// ============================================================================
// 5. CUSTOMIZE INDIRECT MATERIAL FAMILY & CLEANING AREA PARTS
// ============================================================================
function openCustomizeIndirectFamilyModal(existingName = '') {
  const kb = window.INDIRECT_KB || { families: [], family_labels: {} };
  const currentLabel = existingName ? (kb.family_labels?.[existingName] || existingName) : '';
  const isRename = Boolean(existingName);

  const bodyHtml = `
    <div class="space-y-4">
      <div>
        <label class="block font-bold text-slate-700 mb-1">${isRename ? 'Indirect Material Family Code / Short Name' : 'New Indirect Material Family Code / Short Name'}</label>
        <input type="text" id="cust-ind-fam-name" value="${escapeHtml(existingName)}" placeholder="e.g. SS 304, Mn Steel, AiSi 410, SS 316L" class="w-full border border-slate-300 rounded-lg p-2.5 font-mono-code font-bold text-slate-900 bg-white">
        ${isRename ? `<p class="text-[11px] text-slate-500 mt-1">Renaming <strong>${escapeHtml(existingName)}</strong> will automatically update all Cleaning Area parts assigned to this family.</p>` : ''}
      </div>
      <div>
        <label class="block font-bold text-slate-700 mb-1">Full Metallurgical Description / Label</label>
        <input type="text" id="cust-ind-fam-label" value="${escapeHtml(currentLabel)}" placeholder="e.g. Austenitic Stainless Steel (SS 304)" class="w-full border border-slate-300 rounded-lg p-2.5 text-slate-900 bg-white">
      </div>
    </div>
  `;

  openKbCustomizeModal({
    title: isRename ? `Customize Indirect Family: ${existingName}` : 'Add New Indirect Material Family',
    subtitle: 'Indirect Material Source Rule Engine — Stage 1 Classification Taxonomy',
    bodyHtml,
    onSave: async () => {
      const newName = document.getElementById('cust-ind-fam-name').value.trim();
      const label = document.getElementById('cust-ind-fam-label').value.trim();
      if (!newName) {
        alert('Indirect Material Family Name is required.');
        return;
      }
      const res = await fetch('/api/indirect-kb', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': typeof getCSRFToken === 'function' ? getCSRFToken() : '',
        },
        body: JSON.stringify({
          mode: 'family',
          old_name: existingName || null,
          new_name: newName,
          label: label || newName,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.error || 'Failed to save indirect family.');
        return;
      }
      closeKbCustomizeModal();
      window.location.reload();
    },
  });
}
window.openCustomizeIndirectFamilyModal = openCustomizeIndirectFamilyModal;

function openCustomizeIndirectPartModal(sn = null) {
  const kb = window.INDIRECT_KB || { parts: [], families: [] };
  const part = sn ? (kb.parts || []).find(p => Number(p.sn) === Number(sn)) : null;

  const partName = part ? part.part_name : '';
  const location = part ? part.location : 'Cleaning Area';
  const material = part ? part.material : ((kb.families?.[0]?.name) || 'SS 304');
  const elList = part ? (part.elements_list || []) : [
    { element: 'Cr', reference_value: 18.0 },
    { element: 'Ni', reference_value: 8.0 },
    { element: 'Mn', reference_value: 1.5 },
  ];

  const familyOptions = (kb.families || []).map(f =>
    `<option value="${escapeHtml(f.name)}" ${f.name === material ? 'selected' : ''}>${escapeHtml(f.name)} — ${escapeHtml(f.label)}</option>`
  ).join('');

  const elRowsHtml = elList.map(el => renderIndirectPartElementRow(el.element, el.reference_value)).join('');

  const bodyHtml = `
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div>
        <label class="block font-bold text-slate-700 mb-1">Part / Indirect Source Name</label>
        <input type="text" id="cust-ind-part-name" value="${escapeHtml(partName)}" placeholder="e.g. IC Stud Tray" class="w-full border border-slate-300 rounded-lg p-2 font-bold text-slate-900 bg-white">
      </div>
      <div>
        <label class="block font-bold text-slate-700 mb-1">Cleaning Area Location</label>
        <input type="text" id="cust-ind-part-loc" value="${escapeHtml(location)}" placeholder="e.g. Durr Tray Supermarket" class="w-full border border-slate-300 rounded-lg p-2 text-slate-900 bg-white">
      </div>
      <div>
        <label class="block font-bold text-slate-700 mb-1">Material Family</label>
        <select id="cust-ind-part-mat" class="w-full border border-slate-300 rounded-lg p-2 font-mono-code font-bold text-slate-900 bg-white">
          ${familyOptions}
        </select>
      </div>
    </div>

    <div class="p-3 rounded-lg bg-blue-50 border border-blue-200 text-xs text-blue-900 flex flex-wrap items-center justify-between gap-2">
      <span><strong>Automatic Tolerance Calculation:</strong> &lt;1% &rarr; &plusmn;25% &bull; 1–5% &rarr; &plusmn;20% &bull; &gt;5% &rarr; &plusmn;10%</span>
      <span class="font-mono-code text-[11px]">Min = Ref &times; (1 &minus; Tol), Max = Ref &times; (1 + Tol)</span>
    </div>

    <div class="space-y-2">
      <div class="flex items-center justify-between">
        <label class="font-bold text-slate-700 uppercase tracking-wider text-[11px]">Populated Reference Elements (wt%)</label>
        <button type="button" onclick="addIndirectPartElementRow()" class="px-2.5 py-1 rounded border border-slate-300 bg-white hover:bg-slate-50 font-semibold text-slate-700 flex items-center gap-1">
          <span class="material-symbols-outlined text-[14px]">add</span>
          <span>Add Element</span>
        </button>
      </div>
      <div class="border border-slate-200 rounded-lg overflow-hidden">
        <table class="w-full text-left border-collapse text-xs">
          <thead class="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase text-[10px]">
            <tr>
              <th class="py-2 px-3">Element</th>
              <th class="py-2 px-3 text-right">Reference wt%</th>
              <th class="py-2 px-3 text-center">Rule Tolerance</th>
              <th class="py-2 px-3 text-right">Calculated Min – Max wt%</th>
              <th class="py-2 px-3 text-center w-12"></th>
            </tr>
          </thead>
          <tbody id="cust-ind-part-els-tbody" class="divide-y divide-slate-100">
            ${elRowsHtml}
          </tbody>
        </table>
      </div>
    </div>
  `;

  const leftActionsHtml = part
    ? `<button type="button" onclick="deleteIndirectPart(${part.sn})" class="px-3 py-2 rounded-lg text-xs font-bold text-rose-600 hover:bg-rose-50 border border-rose-200 flex items-center gap-1">
         <span class="material-symbols-outlined text-[15px]">delete</span>
         <span>Delete Part</span>
       </button>`
    : '';

  openKbCustomizeModal({
    title: part ? `Customize Indirect Source #${part.sn}: ${part.part_name}` : 'Add New Indirect Material Source Part',
    subtitle: 'Indirect Material Source Rule Engine — Stage 2 Part Matching Reference',
    bodyHtml,
    leftActionsHtml,
    onSave: () => submitCustomizeIndirectPart(part ? part.sn : null),
  });
}
window.openCustomizeIndirectPartModal = openCustomizeIndirectPartModal;

function renderIndirectPartElementRow(sym = '', refVal = '') {
  const preview = computeIndirectTolerancePreview(refVal);
  return `
    <tr class="cust-ind-el-row">
      <td class="p-2">
        <input type="text" class="ind-el-sym w-20 border border-slate-300 rounded p-1.5 font-mono-code font-bold text-slate-900 bg-white" value="${escapeHtml(sym)}" placeholder="Cr">
      </td>
      <td class="p-2 text-right">
        <input type="number" step="0.001" oninput="updateIndirectRowPreview(this)" class="ind-el-val w-28 border border-slate-300 rounded p-1.5 text-right font-mono-code font-bold text-slate-900 bg-white" value="${refVal}">
      </td>
      <td class="p-2 text-center font-mono-code font-bold text-blue-700 ind-el-tol">${preview.tolLabel}</td>
      <td class="p-2 text-right font-mono-code text-slate-600 ind-el-range">${preview.min} – ${preview.max}%</td>
      <td class="p-2 text-center">
        <button type="button" onclick="this.closest('tr').remove()" class="text-rose-600 hover:text-rose-800 p-1">
          <span class="material-symbols-outlined text-[16px]">delete</span>
        </button>
      </td>
    </tr>
  `;
}

function updateIndirectRowPreview(inputEl) {
  const tr = inputEl.closest('tr');
  if (!tr) return;
  const p = computeIndirectTolerancePreview(inputEl.value);
  tr.querySelector('.ind-el-tol').textContent = p.tolLabel;
  tr.querySelector('.ind-el-range').textContent = `${p.min} – ${p.max}%`;
}
window.updateIndirectRowPreview = updateIndirectRowPreview;

function addIndirectPartElementRow() {
  const tbody = document.getElementById('cust-ind-part-els-tbody');
  if (!tbody) return;
  tbody.insertAdjacentHTML('beforeend', renderIndirectPartElementRow('', 1.0));
}
window.addIndirectPartElementRow = addIndirectPartElementRow;

async function submitCustomizeIndirectPart(sn) {
  const part_name = document.getElementById('cust-ind-part-name').value.trim();
  const location = document.getElementById('cust-ind-part-loc').value.trim();
  const material = document.getElementById('cust-ind-part-mat').value.trim();

  if (!part_name || !material) {
    alert('Part Name and Material Family are required.');
    return;
  }

  const elements = {};
  document.querySelectorAll('#cust-ind-part-els-tbody .cust-ind-el-row').forEach(tr => {
    const sym = tr.querySelector('.ind-el-sym').value.trim();
    const val = parseFloat(tr.querySelector('.ind-el-val').value);
    if (sym && !isNaN(val) && val > 0) {
      elements[sym] = val;
    }
  });

  if (Object.keys(elements).length === 0) {
    alert('Please provide at least one populated reference element (> 0 wt%).');
    return;
  }

  const res = await fetch('/api/indirect-kb', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': typeof getCSRFToken === 'function' ? getCSRFToken() : '',
    },
    body: JSON.stringify({
      mode: 'part',
      sn,
      part_name,
      location,
      material,
      elements,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || 'Failed to save indirect part.');
    return;
  }
  closeKbCustomizeModal();
  window.location.reload();
}

async function deleteIndirectPart(sn) {
  if (!confirm('Remove this Indirect Material Source part from the reference library?')) return;
  const res = await fetch('/api/indirect-kb', {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': typeof getCSRFToken === 'function' ? getCSRFToken() : '',
    },
    body: JSON.stringify({ sn }),
  });
  if (res.ok) {
    closeKbCustomizeModal();
    window.location.reload();
  } else {
    alert('Failed to delete indirect source part.');
  }
}
window.deleteIndirectPart = deleteIndirectPart;

// ============================================================================
// 6. CUSTOMIZE CANONICAL COMPONENT FINGERPRINT MODAL
// ============================================================================
function openCustomizeComponentModal(cid = null) {
  const comps = window.KB_COMPONENTS || [];
  const comp = cid ? comps.find(c => c.component_id === cid) : null;

  const displayName = comp ? comp.display_name : '';
  const compId = comp ? comp.component_id : '';
  const matBody = comp ? comp.material_body : 'Standard Reference';
  const famIds = comp ? (comp.family_ids || []).join(', ') : 'F4';
  const quality = comp ? comp.fingerprint_quality : 'MEDIUM';
  const aliases = comp ? comp.aliases : '';
  const elementsObj = comp ? (comp.elements || {}) : {
    Fe: { median: 70.0, q1: 68.0, q3: 72.0, role: 'expected' },
    Cr: { median: 18.0, q1: 17.5, q3: 18.5, role: 'expected' },
  };

  const elRowsHtml = Object.entries(elementsObj)
    .map(([el, st]) => renderComponentElementEditorRow(el, st))
    .join('');

  const bodyHtml = `
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div>
        <label class="block font-bold text-slate-700 mb-1">Component Display Name</label>
        <input type="text" id="cust-comp-name" value="${escapeHtml(displayName)}" placeholder="e.g. Armature Bolt" class="w-full border border-slate-300 rounded-lg p-2 font-bold text-slate-900 bg-white">
      </div>
      <div>
        <label class="block font-bold text-slate-700 mb-1">Material Body / Specification</label>
        <input type="text" id="cust-comp-mat" value="${escapeHtml(matBody)}" placeholder="e.g. Sl2 B1/ 100Cr6" class="w-full border border-slate-300 rounded-lg p-2 text-slate-900 bg-white">
      </div>
      <div>
        <label class="block font-bold text-slate-700 mb-1">Mapped Family IDs (comma-sep)</label>
        <input type="text" id="cust-comp-fams" value="${escapeHtml(famIds)}" placeholder="e.g. F2, F4" class="w-full border border-slate-300 rounded-lg p-2 font-mono-code font-bold text-slate-900 bg-white">
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div>
        <label class="block font-bold text-slate-700 mb-1">Known Aliases (comma-separated)</label>
        <input type="text" id="cust-comp-aliases" value="${escapeHtml(aliases)}" class="w-full border border-slate-300 rounded-lg p-2 text-slate-900 bg-white">
      </div>
      <div>
        <label class="block font-bold text-slate-700 mb-1">Fingerprint Quality Tier</label>
        <select id="cust-comp-quality" class="w-full border border-slate-300 rounded-lg p-2 font-bold text-slate-900 bg-white">
          <option value="HIGH" ${quality === 'HIGH' ? 'selected' : ''}>HIGH (20+ spectra)</option>
          <option value="MEDIUM" ${quality === 'MEDIUM' ? 'selected' : ''}>MEDIUM (5–19 spectra)</option>
          <option value="LOW" ${quality === 'LOW' ? 'selected' : ''}>LOW (1–4 spectra)</option>
        </select>
      </div>
    </div>

    <div class="space-y-2">
      <div class="flex items-center justify-between">
        <label class="font-bold text-slate-700 uppercase tracking-wider text-[11px]">Empirical Element Medians &amp; IQR Bounds (Metal-Basis wt%)</label>
        <button type="button" onclick="addComponentElementEditorRow()" class="px-2.5 py-1 rounded border border-slate-300 bg-white hover:bg-slate-50 font-semibold text-slate-700 flex items-center gap-1">
          <span class="material-symbols-outlined text-[14px]">add</span>
          <span>Add Element</span>
        </button>
      </div>
      <div class="border border-slate-200 rounded-lg overflow-hidden">
        <table class="w-full text-left border-collapse text-xs">
          <thead class="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase text-[10px]">
            <tr>
              <th class="py-2 px-3">Element</th>
              <th class="py-2 px-3 text-right">Median wt%</th>
              <th class="py-2 px-3 text-right">Q1 (25th) wt%</th>
              <th class="py-2 px-3 text-right">Q3 (75th) wt%</th>
              <th class="py-2 px-3">Role</th>
              <th class="py-2 px-3 text-center w-12"></th>
            </tr>
          </thead>
          <tbody id="cust-comp-els-tbody" class="divide-y divide-slate-100">
            ${elRowsHtml}
          </tbody>
        </table>
      </div>
    </div>
  `;

  openKbCustomizeModal({
    title: comp ? `Customize Component Fingerprint: ${comp.display_name}` : 'Add New Canonical Component',
    subtitle: 'Direct Component Scoring Engine — Empirical Median & IQR Reference',
    bodyHtml,
    onSave: () => submitCustomizeComponent(compId),
  });
}
window.openCustomizeComponentModal = openCustomizeComponentModal;

function renderComponentElementEditorRow(el = '', st = {}) {
  const med = Number(st.median ?? 1.0);
  const q1 = Number(st.q1 ?? (med * 0.9).toFixed(2));
  const q3 = Number(st.q3 ?? (med * 1.1).toFixed(2));
  const role = st.role || 'expected';
  return `
    <tr class="cust-comp-el-row">
      <td class="p-2">
        <input type="text" class="comp-el-sym w-20 border border-slate-300 rounded p-1.5 font-mono-code font-bold text-slate-900 bg-white" value="${escapeHtml(el)}" placeholder="Fe">
      </td>
      <td class="p-2">
        <input type="number" step="0.01" class="comp-el-med w-24 border border-slate-300 rounded p-1.5 text-right font-mono-code text-slate-900 bg-white" value="${med}">
      </td>
      <td class="p-2">
        <input type="number" step="0.01" class="comp-el-q1 w-24 border border-slate-300 rounded p-1.5 text-right font-mono-code text-slate-900 bg-white" value="${q1}">
      </td>
      <td class="p-2">
        <input type="number" step="0.01" class="comp-el-q3 w-24 border border-slate-300 rounded p-1.5 text-right font-mono-code text-slate-900 bg-white" value="${q3}">
      </td>
      <td class="p-2">
        <select class="comp-el-role border border-slate-300 rounded p-1.5 text-slate-900 bg-white">
          <option value="expected" ${role === 'expected' ? 'selected' : ''}>expected</option>
          <option value="common" ${role === 'common' ? 'selected' : ''}>common</option>
          <option value="rare" ${role === 'rare' ? 'selected' : ''}>rare</option>
        </select>
      </td>
      <td class="p-2 text-center">
        <button type="button" onclick="this.closest('tr').remove()" class="text-rose-600 hover:text-rose-800 p-1">
          <span class="material-symbols-outlined text-[16px]">delete</span>
        </button>
      </td>
    </tr>
  `;
}

function addComponentElementEditorRow() {
  const tbody = document.getElementById('cust-comp-els-tbody');
  if (!tbody) return;
  tbody.insertAdjacentHTML('beforeend', renderComponentElementEditorRow('', { median: 1.0, q1: 0.8, q3: 1.2, role: 'common' }));
}
window.addComponentElementEditorRow = addComponentElementEditorRow;

async function submitCustomizeComponent(existingCid) {
  const display_name = document.getElementById('cust-comp-name').value.trim();
  const material_body = document.getElementById('cust-comp-mat').value.trim();
  const famsRaw = document.getElementById('cust-comp-fams').value;
  const aliases = document.getElementById('cust-comp-aliases').value.trim();
  const fingerprint_quality = document.getElementById('cust-comp-quality').value;

  if (!display_name) {
    alert('Component Display Name is required.');
    return;
  }

  const family_ids = famsRaw.split(',').map(s => s.trim()).filter(Boolean);
  const elements = {};
  document.querySelectorAll('#cust-comp-els-tbody .cust-comp-el-row').forEach(tr => {
    const sym = tr.querySelector('.comp-el-sym').value.trim();
    const median = parseFloat(tr.querySelector('.comp-el-med').value) || 0;
    const q1 = parseFloat(tr.querySelector('.comp-el-q1').value) || 0;
    const q3 = parseFloat(tr.querySelector('.comp-el-q3').value) || 0;
    const role = tr.querySelector('.comp-el-role').value;
    if (sym) {
      elements[sym] = { median, q1, q3, role };
    }
  });

  const cid = existingCid || display_name.toUpperCase().replace(/[^A-Z0-9]+/g, '_');
  const res = await fetch(`/api/components/${encodeURIComponent(cid)}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': typeof getCSRFToken === 'function' ? getCSRFToken() : '',
    },
    body: JSON.stringify({
      component_id: cid,
      display_name,
      material_body,
      family_ids,
      aliases,
      fingerprint_quality,
      elements,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || 'Failed to save component customization.');
    return;
  }
  closeKbCustomizeModal();
  window.location.reload();
}

// ============================================================================
// 7. INSPECT COMPONENT DETAIL MODAL (READ-ONLY VIEW WITH QUICK CUSTOMIZE BUTTON)
// ============================================================================
function openComponentDetailModal(comp) {
  if (!comp || !window.openAppModal) return;

  fetch(`/api/components/${encodeURIComponent(comp.component_id || comp.id)}`)
    .then(res => res.json())
    .then(data => {
      const elements = data.elements || {};
      const rows = Object.entries(elements).map(([el, st]) => `
        <tr class="hover:bg-slate-50 border-b border-slate-100 font-mono-code text-xs">
          <td class="py-1.5 px-3 font-bold text-slate-800">${escapeHtml(el)}</td>
          <td class="py-1.5 px-3 text-right">${Number(st.median).toFixed(2)}%</td>
          <td class="py-1.5 px-3 text-right text-slate-500">${Number(st.q1).toFixed(2)}% – ${Number(st.q3).toFixed(2)}%</td>
          <td class="py-1.5 px-3 text-right">${Number(st.iqr).toFixed(2)}</td>
          <td class="py-1.5 px-3 text-center">
            <span class="px-1.5 py-0.5 rounded text-[10px] uppercase font-bold ${st.role === 'expected' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'}">
              ${escapeHtml(st.role)}
            </span>
          </td>
        </tr>
      `).join('');

      const content = `
        <div class="space-y-4">
          <div class="p-3 bg-slate-50 border border-slate-200 rounded text-xs">
            <div class="font-bold text-slate-900">${escapeHtml(data.display_name || comp.name)}</div>
            <div class="text-slate-500 font-mono-code mt-0.5">Component ID: ${escapeHtml(data.component_id)} &bull; ${data.sample_count} Reference Spectra</div>
            <div class="text-slate-600 mt-2">Material Body: <strong>${escapeHtml(data.material_body || 'Standard Reference')}</strong></div>
          </div>

          <div>
            <div class="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Empirical Element Medians &amp; IQR Bounds</div>
            <div class="max-h-60 overflow-y-auto border border-slate-200 rounded">
              <table class="w-full text-left text-xs border-collapse">
                <thead class="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase font-bold text-[10px]">
                  <tr>
                    <th class="py-2 px-3">Element</th>
                    <th class="py-2 px-3 text-right">Median wt%</th>
                    <th class="py-2 px-3 text-right">IQR Band (Q1-Q3)</th>
                    <th class="py-2 px-3 text-right">IQR Width</th>
                    <th class="py-2 px-3 text-center">Role</th>
                  </tr>
                </thead>
                <tbody>
                  ${rows || '<tr><td colspan="5" class="p-3 text-center text-slate-500">No empirical elements logged.</td></tr>'}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      `;

      window.openAppModal({
        title: comp.name || data.display_name,
        subtitle: 'Empirical Metallurgical Fingerprint',
        contentHtml: content,
        actionsHtml: `
          <button type="button" onclick="window.closeAppModal(); openCustomizeComponentModal('${escapeHtml(data.component_id)}')" class="px-4 py-2 text-xs font-bold rounded bg-[#ED0007] text-white hover:bg-[#c90006]">
            Customize Component
          </button>
          <button type="button" onclick="window.closeAppModal()" class="px-4 py-2 text-xs font-semibold rounded bg-slate-900 text-white hover:bg-slate-800">
            Close
          </button>
        `,
      });
    })
    .catch(() => {
      alert('Failed to load component statistical fingerprint.');
    });
}
window.openComponentDetailModal = openComponentDetailModal;
