/**
 * static/js/knowledge.js
 * ======================
 * Controller for DHATU BODH Knowledge Base screen.
 * Handles tab switching (Families, Components, Gates), universal search,
 * family detail selection, and empirical component fingerprint modal.
 */

let activeKbTab = 'families';

function switchKbTab(tab) {
  activeKbTab = tab;

  // Toggle views
  const viewFam = document.getElementById('kb-view-families');
  const viewComp = document.getElementById('kb-view-components');
  const viewSpectra = document.getElementById('kb-view-spectra');
  const viewGates = document.getElementById('kb-view-gates');

  if (viewFam) viewFam.classList.toggle('hidden', tab !== 'families');
  if (viewComp) viewComp.classList.toggle('hidden', tab !== 'components');
  if (viewSpectra) viewSpectra.classList.toggle('hidden', tab !== 'spectra');
  if (viewGates) viewGates.classList.toggle('hidden', tab !== 'gates');

  // Toggle button active states
  const btnFam = document.getElementById('tab-btn-families');
  const btnComp = document.getElementById('tab-btn-components');
  const btnSpectra = document.getElementById('tab-btn-spectra');
  const btnGates = document.getElementById('tab-btn-gates');

  const activeClass = 'px-3.5 py-1.5 rounded-md bg-white text-slate-900 shadow-xs transition-all font-bold';
  const inactiveClass = 'px-3.5 py-1.5 rounded-md text-slate-600 hover:text-slate-900 transition-all font-medium';

  if (btnFam) btnFam.className = tab === 'families' ? activeClass : inactiveClass;
  if (btnComp) btnComp.className = tab === 'components' ? activeClass : inactiveClass;
  if (btnSpectra) btnSpectra.className = tab === 'spectra' ? activeClass : inactiveClass;
  if (btnGates) btnGates.className = tab === 'gates' ? activeClass : inactiveClass;

  // Re-run search query if present
  const searchInput = document.getElementById('kb-search-input');
  if (searchInput && searchInput.value) {
    handleKbSearch(searchInput.value);
  }
}
window.switchKbTab = switchKbTab;

function handleKbSearch(query) {
  const q = query.toLowerCase().trim();

  if (activeKbTab === 'families') {
    const items = document.querySelectorAll('.family-item');
    items.forEach(item => {
      const code = (item.getAttribute('data-code') || '').toLowerCase();
      const name = (item.getAttribute('data-name') || '').toLowerCase();
      const desc = (item.getAttribute('data-desc') || '').toLowerCase();
      if (!q || code.includes(q) || name.includes(q) || desc.includes(q)) {
        item.classList.remove('hidden');
      } else {
        item.classList.add('hidden');
      }
    });
  } else if (activeKbTab === 'components') {
    const rows = document.querySelectorAll('.component-row');
    rows.forEach(row => {
      const name = (row.getAttribute('data-name') || '').toLowerCase();
      const id = (row.getAttribute('data-id') || '').toLowerCase();
      const mat = (row.getAttribute('data-mat') || '').toLowerCase();
      const aliases = (row.getAttribute('data-aliases') || '').toLowerCase();
      if (!q || name.includes(q) || id.includes(q) || mat.includes(q) || aliases.includes(q)) {
        row.classList.remove('hidden');
      } else {
        row.classList.add('hidden');
      }
    });
  } else if (activeKbTab === 'spectra') {
    const rows = document.querySelectorAll('.spectrum-row');
    rows.forEach(row => {
      const id = (row.getAttribute('data-id') || '').toLowerCase();
      const comp = (row.getAttribute('data-comp') || '').toLowerCase();
      const summary = (row.getAttribute('data-summary') || '').toLowerCase();
      if (!q || id.includes(q) || comp.includes(q) || summary.includes(q)) {
        row.classList.remove('hidden');
      } else {
        row.classList.add('hidden');
      }
    });
  } else if (activeKbTab === 'gates') {
    const rows = document.querySelectorAll('.gate-row');
    rows.forEach(row => {
      const fam = (row.getAttribute('data-fam') || '').toLowerCase();
      const code = (row.getAttribute('data-code') || '').toLowerCase();
      const name = (row.getAttribute('data-name') || '').toLowerCase();
      if (!q || fam.includes(q) || code.includes(q) || name.includes(q)) {
        row.classList.remove('hidden');
      } else {
        row.classList.add('hidden');
      }
    });
  }
}
window.handleKbSearch = handleKbSearch;

function selectFamily(code) {
  if (!window.KB_FAMILIES) {
    window.location.href = `/knowledge/?family=${code}`;
    return;
  }
  const family = window.KB_FAMILIES.find(f => f.code === code);
  if (!family) return;

  window.ACTIVE_FAMILY = family;

  // Update URL state without reload
  const url = new URL(window.location);
  url.searchParams.set('family', code);
  window.history.pushState({}, '', url);

  // Update left sidebar active highlights
  document.querySelectorAll('.family-item').forEach(item => {
    const itemCode = item.getAttribute('data-code');
    if (itemCode === code) {
      item.className = 'family-item p-3 rounded border cursor-pointer transition-all border-[#ED0007] bg-slate-50 border-l-4';
    } else {
      item.className = 'family-item p-3 rounded border cursor-pointer transition-all border-slate-200 hover:border-slate-300 bg-white';
    }
  });

  // Re-render right column details
  document.getElementById('detail-code-pill').textContent = family.code;
  document.getElementById('detail-status-pill').textContent = `${family.status} SPECIFICATION`;
  document.getElementById('detail-family-name').textContent = family.name;
  document.getElementById('detail-grade-hint').textContent = `Grade hint: ${family.gradeHint}`;
  document.getElementById('detail-description').textContent = family.description || '';
  document.getElementById('btn-edit-profile').setAttribute('href', `/gates/${family.code}/`);

  // Bands table
  const tbody = document.getElementById('bands-table-body');
  tbody.innerHTML = (family.elementBands || []).map(band => `
    <tr class="hover:bg-slate-50 transition-colors">
      <td class="py-2.5 px-4 font-bold text-slate-900">${band.element}</td>
      <td class="py-2.5 px-4">
        ${band.role === 'Required'
          ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-100 text-emerald-800">Required</span>'
          : band.role === 'Trace'
          ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-100 text-amber-800">Trace</span>'
          : '<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-100 text-slate-700">Allowed</span>'}
      </td>
      <td class="py-2.5 px-4 text-right">${(band.rangeMin || band.min_wt_pct || 0).toFixed(1)}%</td>
      <td class="py-2.5 px-4 text-right">${(band.rangeMax || band.max_wt_pct || 0).toFixed(1)}%</td>
      <td class="py-2.5 px-4">
        <div class="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
          <div class="bg-slate-600 h-full" style="width: 75%"></div>
        </div>
      </td>
    </tr>
  `).join('');

  // Ratio gates list
  const gatesList = document.getElementById('family-ratio-gates-list');
  const gates = family.ratioGates || [];
  if (gates.length === 0) {
    gatesList.innerHTML = '<div class="p-4 bg-slate-50 rounded text-xs text-slate-500 text-center">No specific stoichiometric ratio gates enforced for this family. Classification relies on elemental concentration bands.</div>';
  } else {
    gatesList.innerHTML = gates.map(gate => `
      <div class="p-4 bg-slate-50 border border-slate-200 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div>
          <div class="font-bold text-slate-900 text-sm">${gate.name}</div>
          <div class="text-slate-500 font-mono-code mt-0.5">
            Formula: <strong>${gate.numerator} / ${gate.denominator}</strong> &bull; Allowed Band: <strong>${gate.min} – ${gate.max}</strong>
          </div>
          <div class="text-slate-600 mt-2">${gate.rationale || ''}</div>
        </div>
        <span class="px-2.5 py-1 rounded text-xs font-bold uppercase bg-emerald-100 text-emerald-800 shrink-0">
          ACTIVE GATE
        </span>
      </div>
    `).join('');
  }

  // Associated components
  const compGrid = document.getElementById('family-components-grid');
  const compCount = document.getElementById('family-components-count');
  const comps = family.components || [];
  compCount.textContent = `${comps.length} parts`;

  if (comps.length === 0) {
    compGrid.innerHTML = '<div class="col-span-2 p-4 text-center text-slate-500">No components explicitly mapped.</div>';
  } else {
    compGrid.innerHTML = comps.map(c => `
      <div class="p-2.5 bg-slate-50 border border-slate-200 rounded flex items-center justify-between">
        <span class="font-semibold text-slate-800 truncate">${c}</span>
        <span class="text-[10px] font-mono-code text-slate-500 bg-white px-1.5 py-0.5 rounded border border-slate-200">
          ${family.code}
        </span>
      </div>
    `).join('');
  }
}
window.selectFamily = selectFamily;

function openComponentDetailModal(comp) {
  if (!comp || !window.openAppModal) return;

  fetch(`/api/components/${comp.component_id || comp.id}`)
    .then(res => res.json())
    .then(data => {
      const elements = data.elements || {};
      const rows = Object.entries(elements).map(([el, st]) => `
        <tr class="hover:bg-slate-50 border-b border-slate-100 font-mono-code text-xs">
          <td class="py-1.5 px-3 font-bold text-slate-800">${el}</td>
          <td class="py-1.5 px-3 text-right">${st.median.toFixed(2)}%</td>
          <td class="py-1.5 px-3 text-right text-slate-500">${st.q1.toFixed(2)}% – ${st.q3.toFixed(2)}%</td>
          <td class="py-1.5 px-3 text-right">${st.iqr.toFixed(2)}</td>
          <td class="py-1.5 px-3 text-center">
            <span class="px-1.5 py-0.5 rounded text-[10px] uppercase font-bold ${st.role === 'expected' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'}">
              ${st.role}
            </span>
          </td>
        </tr>
      `).join('');

      const content = `
        <div class="space-y-4">
          <div class="p-3 bg-slate-50 border border-slate-200 rounded text-xs">
            <div class="font-bold text-slate-900">${data.display_name || comp.name}</div>
            <div class="text-slate-500 font-mono-code mt-0.5">Component ID: ${data.component_id} • ${data.sample_count} Reference Spectra</div>
            <div class="text-slate-600 mt-2">Material Body: <strong>${data.material_body || 'Standard Reference'}</strong></div>
          </div>

          <div>
            <div class="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Empirical Element Medians & IQR Bounds</div>
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
