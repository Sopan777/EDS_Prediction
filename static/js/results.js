/**
 * static/js/results.js
 * ====================
 * Controller for the Dedicated Multi-Spectrum Prediction Results & Interactive Editing Page (/analyzer/results/).
 * Displays every extracted spectrum (excluding Mean/Std/Min/Max), its individual Material Family
 * and Component/Internal Source predictions, and allows inline editing + live re-prediction of any spectrum.
 */

let reportPredictionState = null;
let openEditorIndices = new Set();

function getCSRFToken() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : '';
}

function getSupportedElements() {
  if (Array.isArray(window.DATASET_ELEMENTS) && window.DATASET_ELEMENTS.length > 0) {
    return window.DATASET_ELEMENTS;
  }
  return [
    { symbol: 'Fe', name: 'Iron' },
    { symbol: 'Cr', name: 'Chromium' },
    { symbol: 'Ni', name: 'Nickel' },
    { symbol: 'Mn', name: 'Manganese' },
    { symbol: 'Si', name: 'Silicon' },
    { symbol: 'C', name: 'Carbon' },
    { symbol: 'Mo', name: 'Molybdenum' },
    { symbol: 'Cu', name: 'Copper' },
    { symbol: 'Sn', name: 'Tin' },
    { symbol: 'Al', name: 'Aluminium' },
    { symbol: 'Zn', name: 'Zinc' },
    { symbol: 'W', name: 'Tungsten' },
    { symbol: 'V', name: 'Vanadium' },
    { symbol: 'O', name: 'Oxygen' },
    { symbol: 'P', name: 'Phosphorus' },
    { symbol: 'S', name: 'Sulfur' },
    { symbol: 'F', name: 'Fluorine' },
    { symbol: 'Pb', name: 'Lead' },
    { symbol: 'Au', name: 'Gold' },
    { symbol: 'N', name: 'Nitrogen' },
    { symbol: 'Ca', name: 'Calcium' },
    { symbol: 'K', name: 'Potassium' },
  ];
}

document.addEventListener('DOMContentLoaded', () => {
  let loaded = null;
  if (window.FORCE_SERVER_PREDICTION && window.INITIAL_PREDICTION_DATA) {
    loaded = window.INITIAL_PREDICTION_DATA;
  } else {
    try {
      const rawSession = sessionStorage.getItem('DHATU_LATEST_PREDICTION');
      if (rawSession) {
        loaded = JSON.parse(rawSession);
      }
    } catch (e) {
      console.warn('Could not read sessionStorage prediction:', e);
    }

    if (!loaded && window.INITIAL_PREDICTION_DATA) {
      loaded = window.INITIAL_PREDICTION_DATA;
    }
  }

  if (!loaded || !Array.isArray(loaded.perSpectrum) || loaded.perSpectrum.length === 0) {
    document.getElementById('results-empty-state').classList.remove('hidden');
    document.getElementById('results-main-content').classList.add('hidden');
    return;
  }

  reportPredictionState = loaded;
  saveStateToSessionStorage();
  renderAllResultsPage();
});

function saveStateToSessionStorage() {
  if (!reportPredictionState) return;
  try {
    sessionStorage.setItem('DHATU_LATEST_PREDICTION', JSON.stringify(reportPredictionState));
  } catch (e) {
    // ignore storage quota errors
  }
}

function renderAllResultsPage() {
  if (!reportPredictionState) return;
  document.getElementById('results-empty-state').classList.add('hidden');
  document.getElementById('results-main-content').classList.remove('hidden');

  renderTopBar();
  renderSummaryTable();
  renderSpectrumCards();
}

/* =========================================================================
   1. Top Report Header & Metadata Strip
   ========================================================================= */

function renderTopBar() {
  const titleEl = document.getElementById('report-main-title');
  const stripEl = document.getElementById('report-metadata-strip');
  const countBadge = document.getElementById('summary-badge-count');

  const spectra = reportPredictionState.perSpectrum || [];
  const fname = reportPredictionState.sourceFilename || 'Uploaded EDS Report';
  const rMeta = reportPredictionState.reportMetadata || {};

  if (titleEl) {
    titleEl.textContent = `${fname} — All Spectrum Predictions (${spectra.length})`;
  }
  if (countBadge) {
    countBadge.textContent = `${spectra.length} Spectrum${spectra.length === 1 ? '' : 's'} Analyzed`;
  }

  const sites = new Set(spectra.map(s => s.siteName || 'Site 1'));
  const pills = [];

  pills.push(`<span class="meta-pill"><span class="material-symbols-outlined text-[14px] text-slate-500">description</span> File: <strong>${escapeHtml(fname)}</strong></span>`);
  pills.push(`<span class="meta-pill"><span class="material-symbols-outlined text-[14px] text-blue-600">layers</span> Sites / Tables: <strong>${sites.size}</strong></span>`);
  pills.push(`<span class="meta-pill"><span class="material-symbols-outlined text-[14px] text-emerald-600">ssid_chart</span> Total Spectra: <strong>${spectra.length}</strong></span>`);

  if (rMeta.report_no) {
    pills.push(`<span class="meta-pill">Report No: <strong>${escapeHtml(rMeta.report_no)}</strong></span>`);
  }
  if (rMeta.complaint_no) {
    pills.push(`<span class="meta-pill">Complaint: <strong>${escapeHtml(rMeta.complaint_no)}</strong></span>`);
  }
  if (rMeta.customer) {
    pills.push(`<span class="meta-pill">Customer: <strong>${escapeHtml(rMeta.customer)}</strong></span>`);
  }
  if (rMeta.injector_no) {
    pills.push(`<span class="meta-pill">Injector: <strong>${escapeHtml(rMeta.injector_no)}</strong></span>`);
  }
  if (rMeta.location) {
    pills.push(`<span class="meta-pill">Location: <strong>${escapeHtml(rMeta.location)}</strong></span>`);
  }

  if (stripEl) {
    stripEl.innerHTML = pills.join('');
  }
}

/* =========================================================================
   2. Executive Summary Table of All Spectra
   ========================================================================= */

function getStatusBadgeHtml(decision) {
  const dec = (decision || '').toLowerCase();
  if (dec === 'identified') {
    return `<span class="status-pill identified">● Identified</span>`;
  }
  if (dec === 'ambiguous') {
    return `<span class="status-pill ambiguous">◐ Candidate Pool</span>`;
  }
  return `<span class="status-pill unknown">○ Needs Review</span>`;
}

function buildOverviewIndirectCellHtml(sp) {
  const ind = sp.indirectSourcePrediction;
  if (!ind) {
    return `<span class="text-slate-400 text-xs">Unknown / Inconclusive</span>`;
  }

  const indDec = (ind.decision || 'unknown').toLowerCase();
  const topInd = ind.topIndirectSource;
  const indCands = ind.candidates || [];
  const indFam = ind.indirectFamily || 'Unknown / Inconclusive';

  if (indDec !== 'unknown' && topInd) {
    const altNames = indCands.slice(1, 3).map(c => `${c.partName} (${c.compatibilityPct}%)`).join(', ');
    return `
      <div class="flex items-center gap-1.5 flex-wrap">
        <span class="px-1.5 py-0.5 rounded bg-blue-900 text-white font-mono-code text-[10px] font-bold">${escapeHtml(topInd.material || indFam)}</span>
        <span class="font-bold text-slate-900">${escapeHtml(topInd.partName)}</span>
        <span class="text-[11px] font-mono-code font-bold text-blue-700">(${topInd.compatibilityPct}%)</span>
      </div>
      <div class="text-[11px] text-slate-500 mt-0.5">
        ${topInd.location ? `Loc: ${escapeHtml(topInd.location)}` : ''}
        ${topInd.withinToleranceElements && topInd.withinToleranceElements.length > 0 ? ` • In tol: ${escapeHtml(topInd.withinToleranceElements.join(', '))}` : ''}
      </div>
      ${altNames ? `<div class="text-[11px] text-slate-500">Also plausible: ${escapeHtml(altNames)}</div>` : ''}
    `;
  }

  return `
    <div class="font-bold text-slate-500 text-xs">Unknown / Inconclusive</div>
    <div class="text-[11px] text-slate-400 mt-0.5">
      ${indFam !== 'Unknown / Inconclusive' ? `Family: ${escapeHtml(indFam)} (Outside tolerance)` : 'No matching indirect family'}
    </div>
  `;
}

function renderSummaryTable() {
  const tbody = document.getElementById('all-spectra-summary-tbody');
  if (!tbody) return;

  const spectra = reportPredictionState.perSpectrum || [];
  tbody.innerHTML = spectra.map((sp, idx) => {
    const comp = sp.composition || {};
    const elBadges = Object.entries(comp)
      .map(([el, val]) => `<span class="px-2 py-0.5 rounded bg-slate-100 border border-slate-200 font-mono-code text-[11px] font-bold text-slate-800">${escapeHtml(el)}: ${Number(val).toFixed(2)}%</span>`)
      .join(' ');

    const famCode = sp.familyCode && sp.familyCode !== 'NONE' ? sp.familyCode : '—';
    const famName = sp.family || 'Unclassified';
    const compatPct = sp.compatibilityPct !== undefined ? sp.compatibilityPct : 0;

    const cands = sp.candidateComponents || [];
    let compHtml = '<span class="text-slate-400 text-xs">No confident internal match</span>';
    if (cands.length > 0 && sp.decision !== 'unknown') {
      const top1 = cands[0];
      const runnerUps = cands.slice(1, 3).map(c => c.name).join(', ');
      compHtml = `
        <div class="font-bold text-slate-900">${escapeHtml(top1.name)} <span class="text-[11px] font-mono-code text-emerald-700">(${top1.confidence || compatPct}%)</span></div>
        ${runnerUps ? `<div class="text-[11px] text-slate-500">Also compatible: ${escapeHtml(runnerUps)}</div>` : ''}
      `;
    } else if (cands.length > 0) {
      const topNames = cands.slice(0, 2).map(c => `${c.name} (${c.confidence}%)`).join(', ');
      compHtml = `<div class="text-xs text-slate-600">Closest ref: ${escapeHtml(topNames)}</div>`;
    }

    const indirectHtml = buildOverviewIndirectCellHtml(sp);

    return `
      <tr>
        <td class="font-mono-code font-bold text-slate-700">#${idx + 1}</td>
        <td>
          <div class="font-bold text-slate-900">${escapeHtml(sp.label || `Spectrum ${idx + 1}`)}</div>
          <div class="text-[11px] text-slate-500">Page ${sp.page || 1} • ${escapeHtml(sp.siteName || 'Site 1')}</div>
        </td>
        <td>
          <div class="flex flex-wrap gap-1 max-w-md">${elBadges}</div>
        </td>
        <td>
          <div class="flex items-center gap-1.5">
            <span class="px-1.5 py-0.5 rounded bg-slate-800 text-white font-mono-code text-[10.5px] font-bold">${escapeHtml(famCode)}</span>
            <span class="font-bold text-slate-900">${escapeHtml(famName)}</span>
          </div>
          <div class="text-[11px] text-slate-500 mt-0.5">
            Compatibility: <strong class="font-mono-code text-slate-800">${compatPct}%</strong>
            ${sp.gradeHint ? ` • Grade: ${escapeHtml(sp.gradeHint)}` : ''}
          </div>
        </td>
        <td>${compHtml}</td>
        <td>${indirectHtml}</td>
        <td>${getStatusBadgeHtml(sp.decision)}</td>
        <td style="text-align: right;">
          <button type="button" onclick="jumpAndEditSpectrum(${idx})" class="btn-outline" style="padding: 5px 10px; font-size: 11.5px;">
            <span class="material-symbols-outlined text-[14px] text-blue-600">edit</span>
            <span>Edit Values</span>
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

/* =========================================================================
   3. Detailed Per-Spectrum Cards & Inline Value Editor
   ========================================================================= */

function renderSpectrumCards() {
  const container = document.getElementById('per-spectrum-cards-container');
  if (!container) return;

  const spectra = reportPredictionState.perSpectrum || [];
  container.innerHTML = spectra.map((sp, idx) => buildSingleSpectrumCardHtml(sp, idx)).join('');
}

function buildIndirectCardBoxHtml(sp) {
  const ind = sp.indirectSourcePrediction || {};
  const indDec = (ind.decision || 'unknown').toLowerCase();
  const indFam = ind.indirectFamily || 'Unknown / Inconclusive';
  const indFamLabel = ind.indirectFamilyLabel || indFam;
  const topInd = ind.topIndirectSource || null;
  const indCands = ind.candidates || [];

  const badgeClass = indDec === 'identified'
    ? 'bg-blue-700 text-white'
    : (indDec === 'ambiguous' ? 'bg-amber-600 text-white' : 'bg-slate-600 text-white');

  let checksHtml = '';
  if (topInd && Array.isArray(topInd.elementChecks) && topInd.elementChecks.length > 0) {
    const checkPills = topInd.elementChecks.map(chk => {
      if (chk.status === 'within_tolerance') {
        return `<span class="px-1.5 py-0.5 rounded bg-emerald-100 border border-emerald-300 text-emerald-900 font-mono-code text-[10px] font-bold" title="Ref: ${chk.referenceValue}% (${chk.toleranceLabel}: ${chk.minValue}–${chk.maxValue}%)">✓ ${escapeHtml(chk.element)}: ${chk.measuredValue}% [${chk.minValue}–${chk.maxValue}]</span>`;
      }
      if (chk.status === 'outside_tolerance') {
        return `<span class="px-1.5 py-0.5 rounded bg-amber-100 border border-amber-300 text-amber-900 font-mono-code text-[10px] font-bold" title="Ref: ${chk.referenceValue}% (${chk.toleranceLabel}: ${chk.minValue}–${chk.maxValue}%)">! ${escapeHtml(chk.element)}: ${chk.measuredValue}% [${chk.minValue}–${chk.maxValue}]</span>`;
      }
      return `<span class="px-1.5 py-0.5 rounded bg-slate-100 border border-slate-300 text-slate-600 font-mono-code text-[10px]" title="Ref: ${chk.referenceValue}% (Not detected in EDS)">○ ${escapeHtml(chk.element)} (Ref ${chk.referenceValue}%)</span>`;
    }).join(' ');
    checksHtml = `<div class="flex flex-wrap gap-1 mt-2">${checkPills}</div>`;
  }

  const indCandRowsHtml = indCands.slice(0, 4).map((c, cIdx) => `
    <tr class="border-b border-blue-200/60 last:border-none text-xs">
      <td class="py-1.5 pr-2 font-mono-code font-bold text-slate-500">#${cIdx + 1}</td>
      <td class="py-1.5 px-2">
        <div class="font-bold text-slate-900">${escapeHtml(c.partName)}</div>
        <div class="text-[10px] text-slate-500">${escapeHtml(c.location || '')}</div>
      </td>
      <td class="py-1.5 px-2">
        <span class="px-1.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-white border border-blue-200 text-blue-900">
          ${escapeHtml(c.material)}
        </span>
      </td>
      <td class="py-1.5 pl-2 text-right font-mono-code font-bold text-slate-900">${c.compatibilityPct}%</td>
    </tr>
  `).join('');

  return `
    <div class="pred-box-indirect">
      <div class="flex items-center justify-between gap-2">
        <span class="text-[11px] font-bold uppercase tracking-wider text-blue-800">3. Probable Indirect Source</span>
        <span class="px-2 py-0.5 rounded font-mono-code text-[10.5px] font-bold ${badgeClass}">
          ${escapeHtml(indFam)}
        </span>
      </div>

      <div class="text-[11px] text-slate-600 mt-1">
        Stage 1 Indirect Family: <strong>${escapeHtml(indFamLabel)}</strong>
      </div>

      ${topInd && indDec !== 'unknown' ? `
        <div class="mt-2 flex items-baseline justify-between gap-2">
          <div>
            <span class="text-lg font-black text-slate-900">${escapeHtml(topInd.partName)}</span>
            ${topInd.location ? `<div class="text-[11px] text-slate-600">Location: <strong>${escapeHtml(topInd.location)}</strong></div>` : ''}
          </div>
          <span class="px-2 py-0.5 rounded bg-blue-100 text-blue-900 border border-blue-300 font-mono-code text-xs font-bold shrink-0">
            ${topInd.compatibilityPct}% Match
          </span>
        </div>
        ${checksHtml}
        <p class="text-[11px] text-slate-600 mt-1.5">${escapeHtml(topInd.notes || '')}</p>
      ` : `
        <div class="text-sm font-black text-slate-700 mt-2">Unknown / Inconclusive</div>
        <p class="text-[11.5px] text-slate-600 mt-1 leading-relaxed">
          ${escapeHtml(ind.stage1Reason || 'Measured EDS elemental values do not match any Cleaning Area indirect material source within tolerance.')}
        </p>
      `}

      ${indCandRowsHtml && indDec !== 'unknown' ? `
        <div class="mt-3 pt-2 border-t border-blue-200/80">
          <div class="text-[10px] font-bold uppercase text-blue-800 mb-1">Cleaning Area Reference Matches (±25% / ±20% / ±10% Tol)</div>
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="text-[10px] font-bold uppercase text-slate-500 border-b border-blue-200/80">
                <th class="pb-1">Rank</th>
                <th class="pb-1 px-2">Indirect Part</th>
                <th class="pb-1 px-2">Material</th>
                <th class="pb-1 text-right">Compat.</th>
              </tr>
            </thead>
            <tbody>
              ${indCandRowsHtml}
            </tbody>
          </table>
        </div>
      ` : ''}
    </div>
  `;
}

function buildSingleSpectrumCardHtml(sp, idx) {
  const dec = (sp.decision || 'unknown').toLowerCase();
  const statusClass = dec === 'identified' ? 'status-identified' : (dec === 'ambiguous' ? 'status-ambiguous' : 'status-unknown');
  const isEditorOpen = openEditorIndices.has(idx);

  const comp = sp.composition || {};
  const metalBasis = sp.metalBasisComposition || {};
  const totalWt = Object.values(comp).reduce((acc, v) => acc + (parseFloat(v) || 0), 0);

  // Display boxes for each element
  const elBoxesHtml = Object.entries(comp).map(([el, val]) => {
    const numVal = Number(val).toFixed(2);
    const mbVal = metalBasis[el] !== undefined ? `Metal: ${Number(metalBasis[el]).toFixed(1)}%` : 'Non-alloy';
    return `
      <div class="el-val-box">
        <div class="el-sym">
          <span>${escapeHtml(el)}</span>
          <span class="text-[9.5px] font-normal text-slate-400">wt%</span>
        </div>
        <div class="el-num">${numVal}%</div>
        <div class="text-[10px] text-slate-400 mt-0.5">${mbVal}</div>
      </div>
    `;
  }).join('');

  // Editable grid inputs
  const editItemsHtml = Object.entries(comp).map(([el, val]) => `
    <div class="el-edit-item">
      <div class="flex items-center justify-between">
        <label class="text-xs font-bold text-slate-800">${escapeHtml(el)} (wt%)</label>
        <button type="button" onclick="removeElementFromSpectrum(${idx}, '${escapeHtml(el)}')" class="text-xs text-slate-400 hover:text-rose-600 font-bold" title="Remove ${escapeHtml(el)}">×</button>
      </div>
      <input type="number" step="0.01" min="0" max="100"
        id="spec-${idx}-el-${escapeHtml(el)}"
        data-spec-idx="${idx}"
        data-el-sym="${escapeHtml(el)}"
        value="${Number(val).toFixed(2)}"
        onchange="onSpectrumInputChanged(${idx}, '${escapeHtml(el)}', this.value)">
    </div>
  `).join('');

  // Unselected elements for "+ Add Element" dropdown
  const existingSet = new Set(Object.keys(comp));
  const availableToAdd = getSupportedElements().filter(item => !existingSet.has(item.symbol));
  const addOptionsHtml = availableToAdd
    .map(item => `<option value="${item.symbol}">${item.symbol} — ${item.name}</option>`)
    .join('');

  // Candidate components list
  const cands = sp.candidateComponents || [];
  const topCand = cands[0] || null;
  const candRowsHtml = cands.slice(0, 5).map((c, cIdx) => {
    const score = c.confidence !== undefined ? c.confidence : Math.round((c.compatibility || 0) * 100);
    return `
      <tr class="border-b border-slate-200/70 last:border-none text-xs">
        <td class="py-2 pr-2 font-mono-code font-bold text-slate-500">#${cIdx + 1}</td>
        <td class="py-2 px-2 font-bold text-slate-900">${escapeHtml(c.name)}</td>
        <td class="py-2 px-2">
          <span class="px-1.5 py-0.5 rounded text-[10px] font-mono-code font-bold bg-white border border-slate-200 text-slate-700">
            ${escapeHtml(c.fingerprintQuality || 'REF')} (${c.sampleCount || 0})
          </span>
        </td>
        <td class="py-2 pl-2 text-right font-mono-code font-bold text-slate-900">${score}%</td>
      </tr>
    `;
  }).join('');

  const caveats = sp.caveats || [];
  const caveatsHtml = caveats.slice(0, 2).map(c => `
    <div class="text-[11px] text-slate-600 flex items-start gap-1.5 mt-1">
      <span class="material-symbols-outlined text-[14px] text-amber-600 shrink-0 mt-0.5">info</span>
      <span>${escapeHtml(c)}</span>
    </div>
  `).join('');

  const indirectBoxHtml = buildIndirectCardBoxHtml(sp);

  return `
    <div id="spectrum-card-${idx}" class="spectrum-card ${statusClass}">
      <!-- Card Header -->
      <div class="spectrum-card-header">
        <div class="flex flex-wrap items-center gap-3">
          <span class="px-2.5 py-1 rounded-md bg-[#0B2239] text-white font-mono-code text-xs font-bold">
            Spectrum #${idx + 1}
          </span>
          <div>
            <h3 class="text-base font-black text-slate-900">${escapeHtml(sp.label || `Spectrum ${idx + 1}`)}</h3>
            <p class="text-xs text-slate-500">
              Page ${sp.page || 1} • ${escapeHtml(sp.siteName || 'Site 1')}
              ${sp.chemistryMeta ? ` • Report Chemistry: <strong>${escapeHtml(sp.chemistryMeta)}</strong>` : ''}
              ${sp.surfaceCoatingMeta ? ` • Coating: <strong>${escapeHtml(sp.surfaceCoatingMeta)}</strong>` : ''}
            </p>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2.5">
          ${getStatusBadgeHtml(sp.decision)}
          <span class="px-2.5 py-1 rounded-md bg-white border border-slate-200 font-mono-code text-xs font-bold text-slate-800">
            Compatibility: ${sp.compatibilityPct || 0}%
          </span>
          <button type="button" onclick="toggleSpectrumEditor(${idx})" class="${isEditorOpen ? 'btn-navy' : 'btn-outline'}">
            <span class="material-symbols-outlined text-[15px]">${isEditorOpen ? 'expand_less' : 'edit'}</span>
            <span>${isEditorOpen ? 'Close Editor' : 'Edit Spectrum Values'}</span>
          </button>
        </div>
      </div>

      <!-- Card Body -->
      <div class="spectrum-card-body">
        <!-- Elemental Composition Display -->
        <div>
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="text-xs font-bold uppercase tracking-wider text-slate-600">
              Extracted Elemental Composition (wt%)
            </span>
            <span class="text-xs font-mono-code text-slate-500">
              Measured Total: <strong class="text-slate-900">${totalWt.toFixed(2)}%</strong>
              • Alloy Basis Signal: <strong class="text-slate-900">${sp.alloyTotalPct !== undefined ? sp.alloyTotalPct : totalWt.toFixed(1)}%</strong>
            </span>
          </div>

          <div class="el-badges-row">
            ${elBoxesHtml}
          </div>
        </div>

        <!-- Inline Editable Spectrum Panel -->
        <div id="editor-panel-spec-${idx}" class="el-editor-panel ${isEditorOpen ? '' : 'hidden'}">
          <div class="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-blue-200">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-[18px] text-blue-600">tune</span>
              <span class="text-xs font-bold text-slate-900">Edit Spectrum #${idx + 1} Elemental Values (wt%)</span>
              <span class="text-[11px] text-slate-500">— Modify values, add/remove elements, and click Update &amp; Re-Predict</span>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <!-- Add Element Selector -->
              <div class="flex items-center gap-1">
                <select id="add-el-select-${idx}" class="text-xs rounded-md border border-slate-300 bg-white px-2 py-1 text-slate-800">
                  <option value="">+ Add Element...</option>
                  ${addOptionsHtml}
                </select>
                <button type="button" onclick="addElementToSpectrum(${idx})" class="btn-outline" style="padding: 4px 10px; font-size: 11px;">
                  Add
                </button>
              </div>

              <button type="button" onclick="autoBalanceFeForSpectrum(${idx})" class="btn-outline" style="padding: 4px 10px; font-size: 11px; color: #1D4ED8;">
                <span class="material-symbols-outlined text-[14px]">balance</span>
                <span>Auto-balance Fe</span>
              </button>

              <button type="button" id="btn-save-spec-${idx}" onclick="saveAndRepredictSingleSpectrum(${idx})" class="btn-red" style="padding: 5px 12px; font-size: 11.5px;">
                <span class="material-symbols-outlined text-[15px]">bolt</span>
                <span>Update &amp; Re-Predict Spectrum #${idx + 1}</span>
              </button>
            </div>
          </div>

          <div class="el-editor-grid">
            ${editItemsHtml}
          </div>
        </div>

        <!-- 3-Column Prediction Output:
             1. Predicted Material Family -> 2. Probable Component / Source(s) -> 3. Probable Indirect Source -->
        <div class="pred-three-col">

          <!-- Column 1: Predicted Material Family -->
          <div class="pred-box">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-bold uppercase tracking-wider text-slate-500">1. Predicted Material Family</span>
              <span class="px-2 py-0.5 rounded bg-slate-900 text-white font-mono-code text-xs font-bold">
                ${escapeHtml(sp.familyCode && sp.familyCode !== 'NONE' ? sp.familyCode : 'UNCLASSIFIED')}
              </span>
            </div>

            <div class="text-lg font-black text-slate-900 mt-1.5">
              ${escapeHtml(sp.family || 'Unclassified / Needs Review')}
            </div>

            <div class="text-xs text-slate-600 mt-1">
              Grade / Specification Hint: <strong>${escapeHtml(sp.gradeHint || 'Empirical Reference Band')}</strong>
            </div>

            <!-- Compatibility Bar -->
            <div class="mt-3">
              <div class="flex items-center justify-between text-xs mb-1">
                <span class="font-semibold text-slate-600">Stoichiometric Compatibility</span>
                <span class="font-mono-code font-bold text-slate-900">${sp.compatibilityPct || 0}%</span>
              </div>
              <div class="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                <div class="h-full rounded-full ${sp.compatibilityPct >= 70 ? 'bg-emerald-600' : (sp.compatibilityPct >= 45 ? 'bg-amber-500' : 'bg-slate-400')}"
                  style="width: ${Math.min(100, Math.max(5, sp.compatibilityPct || 0))}%"></div>
              </div>
            </div>

            ${sp.reason ? `<p class="text-xs text-slate-600 mt-2.5 leading-relaxed">${escapeHtml(sp.reason)}</p>` : ''}
            <div class="mt-2">${caveatsHtml}</div>
          </div>

          <!-- Column 2: Probable Component / Source(s) (Direct Injector Component Engine) -->
          <div class="pred-box">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-bold uppercase tracking-wider text-[#ED0007]">2. Probable Component / Source(s)</span>
              <span class="text-[11px] font-mono-code text-slate-500">
                ${cands.length} Candidate${cands.length === 1 ? '' : 's'}
              </span>
            </div>

            ${topCand ? `
              <div class="mt-1.5 flex items-baseline justify-between gap-2">
                <div>
                  <span class="text-lg font-black text-slate-900">${escapeHtml(topCand.name)}</span>
                  <span class="text-xs text-slate-500 ml-1">(${escapeHtml(topCand.fingerprintQuality || 'REF')} Quality)</span>
                </div>
                <span class="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-mono-code text-xs font-bold shrink-0">
                  ${topCand.confidence !== undefined ? topCand.confidence : Math.round((topCand.compatibility || 0) * 100)}% Match
                </span>
              </div>
              <p class="text-[11.5px] text-slate-600 mt-1">${escapeHtml(topCand.notes || '')}</p>
            ` : `
              <div class="text-sm font-bold text-slate-600 mt-2">No single internal component uniquely confirmed</div>
            `}

            ${candRowsHtml ? `
              <div class="mt-3 pt-2 border-t border-slate-200">
                <table class="w-full text-left border-collapse">
                  <thead>
                    <tr class="text-[10px] font-bold uppercase text-slate-400 border-b border-slate-200">
                      <th class="pb-1">Rank</th>
                      <th class="pb-1 px-2">Component / Source</th>
                      <th class="pb-1 px-2">Reference Support</th>
                      <th class="pb-1 text-right">Match</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${candRowsHtml}
                  </tbody>
                </table>
              </div>
            ` : ''}
          </div>

          <!-- Column 3: Probable Indirect Source (Separate Cleaning Area Rule Engine) -->
          ${indirectBoxHtml}

        </div>
      </div>
    </div>
  `;
}

/* =========================================================================
   4. Interactive Spectrum Editing & Live Re-Prediction
   ========================================================================= */

function toggleSpectrumEditor(idx) {
  if (openEditorIndices.has(idx)) {
    openEditorIndices.delete(idx);
  } else {
    openEditorIndices.add(idx);
  }
  renderSpectrumCards();
}
window.toggleSpectrumEditor = toggleSpectrumEditor;

function jumpAndEditSpectrum(idx) {
  openEditorIndices.add(idx);
  renderSpectrumCards();
  const card = document.getElementById(`spectrum-card-${idx}`);
  if (card) {
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}
window.jumpAndEditSpectrum = jumpAndEditSpectrum;

function onSpectrumInputChanged(specIdx, elSym, rawVal) {
  const sp = reportPredictionState.perSpectrum[specIdx];
  if (!sp) return;
  const num = parseFloat(rawVal);
  sp.composition[elSym] = isNaN(num) ? 0 : Math.max(0, Math.round(num * 100) / 100);
}
window.onSpectrumInputChanged = onSpectrumInputChanged;

function addElementToSpectrum(specIdx) {
  const selectEl = document.getElementById(`add-el-select-${specIdx}`);
  if (!selectEl || !selectEl.value) return;
  const sym = selectEl.value;
  const sp = reportPredictionState.perSpectrum[specIdx];
  if (!sp) return;

  sp.composition[sym] = 0.5;
  if (Array.isArray(sp.analysedElements) && !sp.analysedElements.includes(sym)) {
    sp.analysedElements.push(sym);
  }
  openEditorIndices.add(specIdx);
  renderSpectrumCards();
}
window.addElementToSpectrum = addElementToSpectrum;

function removeElementFromSpectrum(specIdx, sym) {
  const sp = reportPredictionState.perSpectrum[specIdx];
  if (!sp || !sp.composition) return;
  if (Object.keys(sp.composition).length <= 1) {
    alert('A spectrum must retain at least one element.');
    return;
  }
  delete sp.composition[sym];
  openEditorIndices.add(specIdx);
  renderSpectrumCards();
}
window.removeElementFromSpectrum = removeElementFromSpectrum;

function autoBalanceFeForSpectrum(specIdx) {
  const sp = reportPredictionState.perSpectrum[specIdx];
  if (!sp || !sp.composition) return;

  let sumOther = 0;
  for (const [el, val] of Object.entries(sp.composition)) {
    if (el === 'Fe') continue;
    sumOther += parseFloat(val) || 0;
  }
  sp.composition['Fe'] = Math.max(0, Math.round((100 - sumOther) * 100) / 100);
  if (Array.isArray(sp.analysedElements) && !sp.analysedElements.includes('Fe')) {
    sp.analysedElements.push('Fe');
  }
  openEditorIndices.add(specIdx);
  renderSpectrumCards();
}
window.autoBalanceFeForSpectrum = autoBalanceFeForSpectrum;

async function saveAndRepredictSingleSpectrum(specIdx) {
  const sp = reportPredictionState.perSpectrum[specIdx];
  if (!sp) return;

  // Collect latest input values from DOM for this spectrum
  const inputs = document.querySelectorAll(`input[data-spec-idx="${specIdx}"]`);
  inputs.forEach(inp => {
    const sym = inp.getAttribute('data-el-sym');
    const val = parseFloat(inp.value);
    if (sym) {
      sp.composition[sym] = isNaN(val) ? 0 : Math.max(0, Math.round(val * 100) / 100);
    }
  });

  const btn = document.getElementById(`btn-save-spec-${specIdx}`);
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="material-symbols-outlined text-[15px] animate-spin">autorenew</span><span>Updating...</span>`;
  }

  try {
    const res = await fetch('/api/predict-spectrum', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({
        analysis_id: reportPredictionState ? reportPredictionState.analysisId : undefined,
        spectrum: sp.composition,
        spectrum_index: specIdx + 1,
        spectrum_meta: {
          spectrum_id: sp.spectrumId || String(specIdx + 1),
          label: sp.label || `Spectrum ${specIdx + 1}`,
          site_name: sp.siteName || 'Site 1',
          table_name: sp.tableName || 'EDS Table',
          page: sp.page || 1,
          analysed_elements: Object.keys(sp.composition),
          chemistry: sp.chemistryMeta,
          surface_coating: sp.surfaceCoatingMeta,
        },
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      alert(data.error || 'Failed to update spectrum prediction.');
      return;
    }

    if (data.spectrumResult) {
      reportPredictionState.perSpectrum[specIdx] = data.spectrumResult;
      if (Array.isArray(reportPredictionState.allSpectra)) {
        reportPredictionState.allSpectra[specIdx] = data.spectrumResult.composition;
      }
      saveStateToSessionStorage();
      renderSummaryTable();
      renderSpectrumCards();
    }
  } catch (err) {
    console.error('Error re-predicting spectrum:', err);
    alert('Network error while re-predicting spectrum.');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<span class="material-symbols-outlined text-[15px]">bolt</span><span>Update & Re-Predict Spectrum #${specIdx + 1}</span>`;
    }
  }
}
window.saveAndRepredictSingleSpectrum = saveAndRepredictSingleSpectrum;

async function repredictAllSpectra() {
  if (!reportPredictionState || !Array.isArray(reportPredictionState.perSpectrum)) return;
  const btn = document.getElementById('btn-repredict-all');
  const txt = document.getElementById('repredict-all-text');
  if (btn) btn.disabled = true;
  if (txt) txt.textContent = 'Re-Predicting All...';

  try {
    const spectraPayload = reportPredictionState.perSpectrum.map(sp => sp.composition);
    const spectraDetails = reportPredictionState.perSpectrum.map((sp, i) => ({
      index: i + 1,
      spectrum_id: sp.spectrumId || String(i + 1),
      label: sp.label || `Spectrum ${i + 1}`,
      site_name: sp.siteName || 'Site 1',
      table_name: sp.tableName || 'EDS Table',
      page: sp.page || 1,
      analysed_elements: Object.keys(sp.composition),
      values: sp.composition,
      chemistry: sp.chemistryMeta,
      surface_coating: sp.surfaceCoatingMeta,
    }));

    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({
        spectra: spectraPayload,
        spectra_details: spectraDetails,
        source_filename: reportPredictionState.sourceFilename,
        report_metadata: reportPredictionState.reportMetadata,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      alert(data.error || 'Failed to re-predict all spectra.');
      return;
    }

    reportPredictionState = data;
    saveStateToSessionStorage();
    renderAllResultsPage();
  } catch (err) {
    console.error('Re-predict all error:', err);
    alert('Failed to re-predict all spectra.');
  } finally {
    if (btn) btn.disabled = false;
    if (txt) txt.textContent = 'Re-Predict All Spectra';
  }
}
window.repredictAllSpectra = repredictAllSpectra;

function exportPredictionsJSON() {
  if (!reportPredictionState) return;
  const blob = new Blob([JSON.stringify(reportPredictionState, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const baseName = (reportPredictionState.sourceFilename || 'eds_report').replace(/\.[^.]+$/, '');
  a.download = `${baseName}_spectrum_predictions.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
window.exportPredictionsJSON = exportPredictionsJSON;

function escapeHtml(str) {
  return String(str === undefined || str === null ? '' : str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
