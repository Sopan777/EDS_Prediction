/**
 * static/js/knowledge.js
 * ======================
 * Interactive filtering and family selection for Knowledge Base screen.
 */

document.addEventListener('DOMContentLoaded', () => {
  const filterInput = document.getElementById('filter-families-input');
  if (filterInput) {
    filterInput.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase().trim();
      const items = document.querySelectorAll('.family-item');

      items.forEach(item => {
        const code = (item.getAttribute('data-code') || '').toLowerCase();
        const name = (item.getAttribute('data-name') || '').toLowerCase();
        const desc = (item.getAttribute('data-desc') || '').toLowerCase();

        if (code.includes(query) || name.includes(query) || desc.includes(query)) {
          item.classList.remove('hidden');
        } else {
          item.classList.add('hidden');
        }
      });
    });
  }
});

function selectFamily(code) {
  if (!window.ALL_FAMILIES) {
    window.location.href = `/knowledge/?family=${code}`;
    return;
  }
  const family = window.ALL_FAMILIES.find(f => f.code === code);
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
      item.className = 'family-item p-3 rounded-lg border cursor-pointer transition-all bg-white border-[#006b5b] border-l-4 border-l-[#006b5b] shadow-sm dark:bg-[#19211e] dark:border-[#00ffcc] dark:border-l-4 dark:border-l-[#00ffcc]';
    } else {
      item.className = 'family-item p-3 rounded-lg border cursor-pointer transition-all bg-white border-[#c0c8c2] hover:border-[#717974] dark:bg-[#0c1512] dark:border-[#3a4a44] dark:hover:border-[#83958d]';
    }
  });

  // Re-render right column details
  document.getElementById('detail-code-pill').textContent = family.code;
  document.getElementById('detail-status-pill').innerHTML = `<span class="material-symbols-outlined text-[13px]">verified</span> ${family.status} FAMILY`;
  document.getElementById('detail-family-name').textContent = family.name;
  document.getElementById('detail-grade-hint').innerHTML = `<span class="material-symbols-outlined text-[15px]">info</span> Grade hint: ${family.gradeHint}`;
  document.getElementById('btn-edit-profile').setAttribute('href', `/gates/${family.code}/`);
  document.getElementById('link-manage-gates').setAttribute('href', `/gates/${family.code}/`);

  // Bands table
  const tbody = document.getElementById('bands-table-body');
  tbody.innerHTML = (family.elementBands || []).map(band => `
    <tr class="hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
      <td class="py-2.5 px-4 font-bold text-[#134231] dark:text-[#00ffcc] font-mono-code">${band.element}</td>
      <td class="py-2.5 px-4">
        ${band.role === 'Required'
          ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-500/20 text-emerald-500">Required</span>'
          : band.role === 'Trace'
          ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-500/20 text-amber-500">Trace</span>'
          : '<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-gray-500/20 text-gray-500">Optional</span>'}
      </td>
      <td class="py-2.5 px-4 text-right font-mono-code">${band.rangeMin}</td>
      <td class="py-2.5 px-4 text-right font-mono-code">${band.rangeMax}</td>
      <td class="py-2.5 px-4">
        <div class="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-800 relative overflow-hidden">
          <div class="absolute top-0 bottom-0 rounded-full bg-emerald-500" style="left: ${band.barOffsetPct}%; width: ${band.barWidthPct}%;"></div>
        </div>
      </td>
      <td class="py-2.5 px-4 text-right font-mono-code opacity-75">${band.spectraSupport}</td>
    </tr>
  `).join('');

  // Ratio gates
  const gatesList = document.getElementById('ratio-gates-list');
  const gates = family.ratioGates || [];
  if (gates.length === 0) {
    gatesList.innerHTML = '<p class="text-[12px] opacity-60 col-span-2 py-2">No ratio gates configured for this family.</p>';
  } else {
    gatesList.innerHTML = gates.map(gate => `
      <div class="p-3 rounded-lg border bg-[#f7f9fb] border-[#c0c8c2] dark:bg-[#151d1a] dark:border-[#3a4a44]">
        <div class="flex justify-between items-center mb-1">
          <span class="font-mono-code font-bold text-[13px] text-[#134231] dark:text-[#00ffcc]">${gate.name}</span>
          <span class="font-mono-code text-[12px] px-2 py-0.5 rounded bg-black/5 dark:bg-white/5">[${gate.min} - ${gate.max}]</span>
        </div>
        <p class="text-[11px] text-[#717974] dark:text-[#b9cbc2]">${gate.rationale || ''}</p>
      </div>
    `).join('');
  }

  // Components grid
  const compGrid = document.getElementById('components-grid');
  const comps = family.candidateComponents || [];
  if (comps.length === 0) {
    compGrid.innerHTML = '<p class="text-[12px] opacity-60 col-span-2 py-2">No candidate components mapped.</p>';
  } else {
    compGrid.innerHTML = comps.map(comp => `
      <div onclick='openComponentModal(${JSON.stringify(comp)})' class="p-3 rounded-lg border cursor-pointer group transition-all bg-[#f7f9fb] border-[#c0c8c2] hover:border-[#134231] dark:bg-[#151d1a] dark:border-[#3a4a44] dark:hover:border-[#00ffcc]">
        <div class="flex justify-between items-start mb-1">
          <span class="font-mono-code text-[11px] font-bold text-emerald-500">${comp.partNumber}</span>
          <span class="text-[11px] opacity-60">${comp.confidence}% Match</span>
        </div>
        <h4 class="font-semibold text-[13px] text-[#191c1e] dark:text-white group-hover:underline">${comp.name}</h4>
        <p class="text-[11px] mt-1 text-[#717974] dark:text-[#83958d]">${comp.nominalAlloy}</p>
      </div>
    `).join('');
  }
}
