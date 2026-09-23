/**
 * static/js/analyzer.js
 * =====================
 * Controller for DHATU BODH EDS Analyzer screen.
 * Handles single/multi-spectrum input, drag-and-drop file ingestion,
 * Fe auto-balancing, declared material conflict detection, and prioritized
 * 7-step metallurgical results display.
 */

let spectraListState = [
  { Cr: 0, Ni: 0, Mn: 0, Si: 0, Fe: 'Bal.', extras: {} }
];
let activeSpectrumIdx = 0;
let extraElementsState = {};
let uploadedFileState = null;
let currentPredictionData = null;
let currentTopCandidate = null;

// Human-readable family names lookup fallback
const FAMILY_NAME_MAP = {
  'F1a': 'Plain / Low-Manganese Carbon Steel',
  'F1b': '~1.5% Manganese Carbon Steel',
  'F1c': 'Silicon-Chromium Spring Steel',
  'F2': 'Low-Alloy Chromium Bearing Steel (100Cr6)',
  'F3': 'High-Speed Tool Steel (M2 / S6-5-2)',
  'F4': 'Austenitic Stainless Steel 18/8 (AISI 304)',
  'F5': 'Nickel-Base Superalloy (Ni-Cr)',
  'F6a': 'Copper-Tin Bronze (CuSn8)',
  'F6b': 'Bimetallic Cu-Sn Bronze on Steel',
  'F7': 'Gold-Plated Electrical Contact',
  'F8a': 'Zinc-Coated / Galvanized Steel',
  'F8b': 'Zinc-Phosphate Conversion Coated Steel',
};

function switchIngestTab(tab) {
  const btnUpload = document.getElementById('tab-btn-upload');
  const btnManual = document.getElementById('tab-btn-manual');
  const uploadSection = document.getElementById('section-file-upload');

  if (tab === 'upload') {
    uploadSection.classList.remove('hidden');
    btnUpload.className = 'px-3 py-1 font-semibold rounded bg-white text-slate-900 shadow-sm transition-all';
    btnManual.className = 'px-3 py-1 font-medium text-slate-600 hover:text-slate-900 transition-all';
  } else {
    uploadSection.classList.add('hidden');
    btnManual.className = 'px-3 py-1 font-semibold rounded bg-white text-slate-900 shadow-sm transition-all';
    btnUpload.className = 'px-3 py-1 font-medium text-slate-600 hover:text-slate-900 transition-all';
  }
}

// Drag & Drop Setup
document.addEventListener('DOMContentLoaded', () => {
  renderSpectrumTabs();

  const dropZone = document.getElementById('drop-zone');
  if (dropZone) {
    ['dragenter', 'dragover'].forEach(name => {
      dropZone.addEventListener(name, (e) => {
        e.preventDefault();
        dropZone.classList.add('border-slate-500', 'bg-slate-100');
      });
    });

    ['dragleave', 'drop'].forEach(name => {
      dropZone.addEventListener(name, (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-slate-500', 'bg-slate-100');
      });
    });

    dropZone.addEventListener('drop', (e) => {
      if (e.dataTransfer && e.dataTransfer.files.length > 0) {
        handleFileSelected(e.dataTransfer.files[0]);
      }
    });
  }
});

/* =========================================================================
   Spectrum & Composition State Management
   ========================================================================= */

function renderSpectrumTabs() {
  const container = document.getElementById('spectrum-tabs-bar');
  if (!container) return;

  container.innerHTML = spectraListState.map((spec, idx) => {
    const isActive = idx === activeSpectrumIdx;
    const activeClass = 'px-2.5 py-1 text-xs font-bold rounded bg-slate-900 text-white shadow-sm transition-all';
    const inactiveClass = 'px-2.5 py-1 text-xs font-medium rounded border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 transition-all';

    return `
      <button type="button" onclick="switchSpectrumTab(${idx})" class="${isActive ? activeClass : inactiveClass}">
        Spectrum ${idx + 1}
      </button>
    `;
  }).join('');

  const badge = document.getElementById('active-spectrum-badge');
  if (badge) {
    const total = spectraListState.length;
    badge.textContent = total > 1 ? `Editing Spectrum ${activeSpectrumIdx + 1} of ${total}` : 'Spectrum 1';
  }

  const delBtn = document.getElementById('btn-delete-spectrum');
  if (delBtn) {
    delBtn.classList.toggle('hidden', spectraListState.length <= 1);
  }
}

function syncCurrentSpectrumFromInputs() {
  if (!spectraListState[activeSpectrumIdx]) return;
  spectraListState[activeSpectrumIdx] = {
    Cr: parseFloat(document.getElementById('input-cr').value) || 0,
    Ni: parseFloat(document.getElementById('input-ni').value) || 0,
    Mn: parseFloat(document.getElementById('input-mn').value) || 0,
    Si: parseFloat(document.getElementById('input-si').value) || 0,
    Fe: document.getElementById('input-fe').value || 'Bal.',
    extras: { ...extraElementsState },
  };
}

function loadSpectrumToInputs(idx) {
  if (!spectraListState[idx]) return;
  const spec = spectraListState[idx];
  document.getElementById('input-cr').value = spec.Cr !== undefined ? spec.Cr : 0;
  document.getElementById('input-ni').value = spec.Ni !== undefined ? spec.Ni : 0;
  document.getElementById('input-mn').value = spec.Mn !== undefined ? spec.Mn : 0;
  document.getElementById('input-si').value = spec.Si !== undefined ? spec.Si : 0;
  document.getElementById('input-fe').value = spec.Fe !== undefined ? spec.Fe : 'Bal.';

  extraElementsState = { ...(spec.extras || {}) };
  renderExtraElements();
}

function switchSpectrumTab(idx) {
  if (idx === activeSpectrumIdx) return;
  syncCurrentSpectrumFromInputs();
  activeSpectrumIdx = idx;
  loadSpectrumToInputs(idx);
  renderSpectrumTabs();
}

function addNewSpectrumTab() {
  syncCurrentSpectrumFromInputs();
  const clonedExtras = {};
  for (const k of Object.keys(extraElementsState)) {
    clonedExtras[k] = 0;
  }
  spectraListState.push({
    Cr: 0,
    Ni: 0,
    Mn: 0,
    Si: 0,
    Fe: 'Bal.',
    extras: clonedExtras,
  });
  activeSpectrumIdx = spectraListState.length - 1;
  loadSpectrumToInputs(activeSpectrumIdx);
  renderSpectrumTabs();
}

function removeCurrentSpectrumTab() {
  if (spectraListState.length <= 1) return;
  spectraListState.splice(activeSpectrumIdx, 1);
  activeSpectrumIdx = Math.max(0, activeSpectrumIdx - 1);
  loadSpectrumToInputs(activeSpectrumIdx);
  renderSpectrumTabs();
}

function autoBalanceFe() {
  syncCurrentSpectrumFromInputs();
  const cr = parseFloat(document.getElementById('input-cr').value) || 0;
  const ni = parseFloat(document.getElementById('input-ni').value) || 0;
  const mn = parseFloat(document.getElementById('input-mn').value) || 0;
  const si = parseFloat(document.getElementById('input-si').value) || 0;
  
  let extrasSum = 0;
  for (const v of Object.values(extraElementsState)) {
    extrasSum += (parseFloat(v) || 0);
  }

  const sumOther = cr + ni + mn + si + extrasSum;
  const feRem = Math.max(0, Math.round((100 - sumOther) * 100) / 100);
  document.getElementById('input-fe').value = feRem.toFixed(2);
  syncCurrentSpectrumFromInputs();
}

function handleFileSelected(file) {
  if (!file) return;
  uploadedFileState = file;

  const statusText = document.getElementById('upload-status-text');
  if (statusText) {
    statusText.innerHTML = `Loaded: <strong class="text-slate-900">${file.name}</strong> (${(file.size / 1024).toFixed(1)} KB)`;
  }

  triggerPrediction();
}

function applyPreset(presetId) {
  if (!presetId || !window.PRESETS_DATA) return;
  const preset = window.PRESETS_DATA.find(p => p.id === presetId);
  if (!preset) return;

  const comp = preset.composition || {};
  document.getElementById('input-cr').value = comp.Cr || 0;
  document.getElementById('input-ni').value = comp.Ni || 0;
  document.getElementById('input-mn').value = comp.Mn || 0;
  document.getElementById('input-si').value = comp.Si || 0;
  document.getElementById('input-fe').value = comp.Fe !== undefined ? comp.Fe : 'Bal.';

  extraElementsState = {};
  for (const [k, v] of Object.entries(comp)) {
    if (!['Cr', 'Ni', 'Mn', 'Si', 'Fe', 'C'].includes(k) && typeof v === 'number') {
      extraElementsState[k] = v;
    }
  }
  renderExtraElements();
  syncCurrentSpectrumFromInputs();
}

function showAddElementForm(show) {
  document.getElementById('btn-show-add-element').classList.toggle('hidden', show);
  document.getElementById('add-element-form').classList.toggle('hidden', !show);
}

function confirmAddExtraElement() {
  const select = document.getElementById('new-element-select');
  const input = document.getElementById('new-element-val');
  const elem = select.value;
  const val = parseFloat(input.value);

  if (!isNaN(val) && elem) {
    extraElementsState[elem] = val;
    input.value = '';
    showAddElementForm(false);
    renderExtraElements();
    syncCurrentSpectrumFromInputs();
  }
}

function removeExtraElement(elem) {
  delete extraElementsState[elem];
  renderExtraElements();
  syncCurrentSpectrumFromInputs();
}

function renderExtraElements() {
  const container = document.getElementById('extra-elements-container');
  const grid = document.getElementById('extra-elements-grid');
  const keys = Object.keys(extraElementsState);

  if (keys.length === 0) {
    container.classList.add('hidden');
    grid.innerHTML = '';
    return;
  }

  container.classList.remove('hidden');
  grid.innerHTML = keys.map(elem => `
    <div class="bg-slate-50 border border-slate-200 rounded p-2.5 relative group">
      <div class="flex items-center justify-between mb-1">
        <label class="text-xs font-bold text-slate-700">${elem}</label>
        <button type="button" onclick="removeExtraElement('${elem}')" class="text-[10px] text-rose-500 hover:text-rose-700 font-bold" title="Remove element">✕</button>
      </div>
      <input type="number" step="0.01" value="${extraElementsState[elem]}" onchange="extraElementsState['${elem}'] = parseFloat(this.value)||0; syncCurrentSpectrumFromInputs();" class="w-full bg-white border border-slate-300 rounded px-2 py-1.5 text-right font-mono-code text-sm font-medium text-slate-900 focus:outline-none focus:border-slate-600">
    </div>
  `).join('');
}

function clearAnalyzerForm() {
  uploadedFileState = null;
  extraElementsState = {};
  spectraListState = [
    { Cr: 0, Ni: 0, Mn: 0, Si: 0, Fe: 'Bal.', extras: {} }
  ];
  activeSpectrumIdx = 0;
  loadSpectrumToInputs(0);
  renderSpectrumTabs();

  const fileInput = document.getElementById('eds-file-input');
  if (fileInput) fileInput.value = '';
  const statusText = document.getElementById('upload-status-text');
  if (statusText) statusText.textContent = 'Drag & Drop EDS Report or Click to Browse';
  const declaredInput = document.getElementById('input-declared-material');
  if (declaredInput) declaredInput.value = '';

  document.getElementById('awaiting-analysis-card').classList.remove('hidden');
  document.getElementById('analysis-results-card').classList.add('hidden');
  document.getElementById('btn-reset-analysis').classList.add('hidden');
  currentPredictionData = null;
  currentTopCandidate = null;
}
window.clearAnalyzerForm = clearAnalyzerForm;

/* =========================================================================
   Execution & Prediction
   ========================================================================= */

async function triggerPrediction() {
  const btn = document.getElementById('btn-predict-family');
  const btnText = document.getElementById('predict-btn-text');
  const spinner = document.getElementById('predict-btn-spinner');
  const declaredMaterial = document.getElementById('input-declared-material') ? document.getElementById('input-declared-material').value.trim() : '';

  btn.disabled = true;
  btnText.textContent = 'Processing EDS Spectrum...';
  spinner.classList.remove('hidden');

  const start = performance.now();

  try {
    let res;
    if (uploadedFileState) {
      const fd = new FormData();
      fd.append('file', uploadedFileState);
      if (declaredMaterial) {
        fd.append('declared_material', declaredMaterial);
      }
      res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken() },
        body: fd,
      });
    } else {
      syncCurrentSpectrumFromInputs();

      const spectraPayload = spectraListState.map(spec => {
        const item = {
          Cr: spec.Cr || 0,
          Ni: spec.Ni || 0,
          Mn: spec.Mn || 0,
          Si: spec.Si || 0,
          Fe: spec.Fe || 'Bal.',
        };
        for (const [k, v] of Object.entries(spec.extras || {})) {
          item[k] = v;
        }
        return item;
      });

      const hasData = spectraPayload.some(s => {
        return (s.Cr || 0) + (s.Ni || 0) + (s.Mn || 0) + (s.Si || 0) +
          Object.entries(s).filter(([k]) => !['Cr', 'Ni', 'Mn', 'Si', 'Fe', 'C'].includes(k)).reduce((acc, [, v]) => acc + (typeof v === 'number' ? v : 0), 0) > 0;
      });

      if (!hasData) {
        alert('Please enter elemental concentrations (wt%) or select a reference preset to perform analysis.');
        return;
      }

      res = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({
          spectra: spectraPayload,
          declared_material: declaredMaterial || undefined,
        }),
      });
    }

    const data = await res.json();
    if (!res.ok) {
      alert(data.error || 'Prediction analysis failed');
      return;
    }

    currentPredictionData = data;

    // Populate extracted multi-spectrum data back into tabs if file uploaded
    if (data.allSpectra && data.allSpectra.length > 0) {
      spectraListState = data.allSpectra.map(spec => {
        const extras = {};
        for (const [k, v] of Object.entries(spec)) {
          if (!['Cr', 'Ni', 'Mn', 'Si', 'Fe', 'C'].includes(k) && typeof v === 'number') {
            extras[k] = v;
          }
        }
        return {
          Cr: spec.Cr !== undefined ? spec.Cr : 0,
          Ni: spec.Ni !== undefined ? spec.Ni : 0,
          Mn: spec.Mn !== undefined ? spec.Mn : 0,
          Si: spec.Si !== undefined ? spec.Si : 0,
          Fe: spec.Fe !== undefined ? spec.Fe : 'Bal.',
          extras,
        };
      });
      activeSpectrumIdx = 0;
      loadSpectrumToInputs(0);
      renderSpectrumTabs();
    }

    renderPredictionResults(data, ((performance.now() - start) / 1000).toFixed(2));
  } catch (err) {
    console.error('Analysis execution error:', err);
    alert('Failed to communicate with the DHATU BODH analysis service.');
  } finally {
    btn.disabled = false;
    btnText.textContent = 'Analyze EDS Spectrum';
    spinner.classList.add('hidden');
  }
}

/* =========================================================================
   Results Rendering (Strict Priority Order 1 to 7)
   ========================================================================= */

function renderPredictionResults(data, elapsedSecs) {
  document.getElementById('awaiting-analysis-card').classList.add('hidden');
  document.getElementById('analysis-results-card').classList.remove('hidden');
  document.getElementById('btn-reset-analysis').classList.remove('hidden');

  // --- 1. PREDICTED MATERIAL FAMILY ---
  document.getElementById('result-duration').textContent = data.processingTime || `${elapsedSecs}s`;

  // Pooled Spectra Badge
  const pooledBadge = document.getElementById('result-pooled-badge');
  const pooledCount = document.getElementById('result-pooled-count');
  if (data.isPooled || (data.spectraCount && data.spectraCount > 1)) {
    pooledBadge.classList.remove('hidden');
    pooledCount.textContent = `${data.spectraCount} SPECTRA POOLED`;
  } else {
    pooledBadge.classList.add('hidden');
  }

  // Decision Badge
  const badge = document.getElementById('result-decision-badge');
  const decision = data.decision || 'identified';
  if (decision === 'identified') {
    badge.className = 'px-2.5 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-200';
    badge.textContent = 'IDENTIFIED';
  } else if (decision === 'ambiguous') {
    badge.className = 'px-2.5 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-amber-100 text-amber-800 border border-amber-200';
    badge.textContent = 'AMBIGUOUS MATCH';
  } else if (decision === 'conflict') {
    badge.className = 'px-2.5 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-rose-100 text-rose-800 border border-rose-200';
    badge.textContent = 'METALLURGICAL CONFLICT';
  } else {
    badge.className = 'px-2.5 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-slate-100 text-slate-700 border border-slate-200';
    badge.textContent = 'UNCLASSIFIED / ABSTAINED';
  }

  // Family Code Badge & Title
  const familyCode = data.familyCode || 'REF';
  const humanFamilyName = FAMILY_NAME_MAP[familyCode] || data.materialFamily || 'Unclassified Material Family';
  document.getElementById('result-family-code-badge').textContent = familyCode;
  document.getElementById('result-material-title').textContent = humanFamilyName;
  document.getElementById('result-grade-hint').textContent = `Grade hint: ${data.gradeHint || 'Standard Reference Library'}`;

  // Compatibility score
  const pct = data.compatibilityPct || 0;
  document.getElementById('gauge-pct-text').textContent = `${pct}%`;
  const gaugeDesc = document.getElementById('gauge-desc-text');
  if (decision === 'identified') {
    gaugeDesc.textContent = `Elemental signature conforms to specification bands for ${humanFamilyName} (${data.gradeHint || ''}) with ${pct}% compatibility.`;
  } else if (decision === 'conflict') {
    gaugeDesc.textContent = data.conflict ? data.conflict.message : 'Measured elemental chemistry contradicts declared specimen metadata.';
  } else {
    gaugeDesc.textContent = data.reason || 'Measured stoichiometry does not exhibit definitive alloy discriminators for a single family.';
  }

  // --- 2. PREDICTED COMPONENT (TOP MATCH) ---
  currentTopCandidate = data.topCandidate || (data.candidateComponents && data.candidateComponents[0]) || null;
  const topCard = document.getElementById('top-predicted-component-card');

  if (currentTopCandidate && topCard) {
    topCard.classList.remove('hidden');
    document.getElementById('top-comp-name').textContent = currentTopCandidate.name;
    const qBadge = currentTopCandidate.fingerprintQuality || 'EMPIRICAL';
    const sCount = currentTopCandidate.sampleCount || 0;
    document.getElementById('top-comp-quality-badge').textContent = `${qBadge} Quality (${sCount} reference spectra)`;
    document.getElementById('top-comp-conf-badge').textContent = `${currentTopCandidate.confidence || Math.round((currentTopCandidate.compatibility || 0) * 100)}% Match`;
    document.getElementById('top-comp-sub').textContent = `Component ID: ${currentTopCandidate.component_id || currentTopCandidate.id} • Nominal Alloy: ${currentTopCandidate.nominalAlloy || 'Standard Material'}`;
    document.getElementById('top-comp-notes').textContent = currentTopCandidate.notes || 'Closest statistical distance against historical EDS reference fingerprints.';

    const evSuff = currentTopCandidate.evidenceSufficiency !== undefined ? Math.round(currentTopCandidate.evidenceSufficiency * 100) : 100;
    document.getElementById('top-comp-evidence').textContent = `Evidence Sufficiency: ${evSuff}%`;

    const matchedStr = currentTopCandidate.matchedElements && currentTopCandidate.matchedElements.length > 0
      ? currentTopCandidate.matchedElements.join(', ')
      : 'Fe, Cr';
    document.getElementById('top-comp-matched-elements').textContent = `Matched Elements: ${matchedStr}`;
  } else if (topCard) {
    topCard.classList.add('hidden');
  }

  // --- 3. COMPOSITION BREAKDOWN (MEASURED VS EXPECTED BANDS) ---
  renderCompositionBreakdown(data);

  // --- 4. RATIO GATE ANALYSIS ---
  renderRatioGates(data);

  // --- 5. ALTERNATIVE CANDIDATES TABLE ---
  renderCandidatesTable(data);

  // --- 6. WARNINGS & CONFLICTS ---
  renderWarningsAndConflicts(data);
}

function renderCompositionBreakdown(data) {
  const tbody = document.getElementById('composition-breakdown-body');
  if (!tbody) return;

  const rawComp = data.extractedComposition || {};
  const activeFam = data.topFamily || {};
  const bands = activeFam.elementBands || [];

  // Map bands by element
  const bandMap = {};
  bands.forEach(b => { bandMap[b.element] = b; });

  const allElements = Array.from(new Set([...Object.keys(rawComp), ...Object.keys(bandMap)]))
    .filter(el => !['C', 'O', 'N', 'F', 'Ca'].includes(el));

  if (allElements.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="py-4 text-center text-slate-500">No elemental breakdown available.</td></tr>`;
    return;
  }

  tbody.innerHTML = allElements.map(el => {
    const val = rawComp[el] !== undefined ? parseFloat(rawComp[el]) : 0;
    const band = bandMap[el];
    let bandStr = '—';
    let statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-100 text-slate-600">Trace / Unbound</span>';
    let fitBar = '<div class="w-24 bg-slate-200 h-1.5 rounded-full overflow-hidden"><div class="bg-slate-400 h-full" style="width: 50%"></div></div>';

    if (band) {
      bandStr = `${band.min_wt_pct.toFixed(1)}% – ${band.max_wt_pct.toFixed(1)}%`;
      if (val >= band.min_wt_pct && val <= band.max_wt_pct) {
        statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-100 text-emerald-800">Within Band</span>';
        fitBar = '<div class="w-24 bg-emerald-100 h-1.5 rounded-full overflow-hidden"><div class="bg-emerald-600 h-full" style="width: 100%"></div></div>';
      } else if (val < band.min_wt_pct) {
        statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-100 text-amber-800">Below Min</span>';
        fitBar = '<div class="w-24 bg-amber-100 h-1.5 rounded-full overflow-hidden"><div class="bg-amber-500 h-full" style="width: 40%"></div></div>';
      } else {
        statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-rose-100 text-rose-800">Above Max</span>';
        fitBar = '<div class="w-24 bg-rose-100 h-1.5 rounded-full overflow-hidden"><div class="bg-rose-600 h-full" style="width: 100%"></div></div>';
      }
    }

    return `
      <tr class="hover:bg-slate-50 transition-colors font-mono-code">
        <td class="py-2.5 px-4 font-bold text-slate-900">${el}</td>
        <td class="py-2.5 px-4 text-right font-semibold text-slate-900">${val.toFixed(2)}%</td>
        <td class="py-2.5 px-4 text-right text-slate-600">${bandStr}</td>
        <td class="py-2.5 px-4">${fitBar}</td>
        <td class="py-2.5 px-4 text-center">${statusBadge}</td>
      </tr>
    `;
  }).join('');
}

function renderRatioGates(data) {
  const container = document.getElementById('ratio-gates-container');
  if (!container) return;

  const gates = data.ratioGates || data.checks || [];

  if (gates.length === 0) {
    container.innerHTML = `
      <div class="p-4 bg-slate-50 rounded text-xs text-slate-500 text-center">
        No stoichiometric ratio gates configured for this candidate family.
      </div>
    `;
    return;
  }

  container.innerHTML = gates.map(gate => {
    const passed = gate.passed !== undefined ? gate.passed : true;
    const name = gate.name || gate.check_name || 'Stoichiometric Ratio Gate';
    const detail = gate.detail || (gate.observed_ratio !== undefined ? `Observed: ${gate.observed_ratio} (Threshold: ${gate.threshold || 'N/A'})` : 'Evaluated via rule engine');
    const badge = passed
      ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-100 text-emerald-800 shrink-0">PASS</span>'
      : '<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-rose-100 text-rose-800 shrink-0">FAIL</span>';

    return `
      <div class="p-3 bg-slate-50 border border-slate-200 rounded flex items-center justify-between gap-3 text-xs">
        <div class="flex items-center gap-2 min-w-0">
          <span class="material-symbols-outlined text-[18px] ${passed ? 'text-emerald-600' : 'text-rose-600'} shrink-0">
            ${passed ? 'check_circle' : 'cancel'}
          </span>
          <div class="min-w-0">
            <div class="font-bold text-slate-900 truncate">${name}</div>
            <div class="text-[11px] text-slate-500 font-mono-code">${detail}</div>
          </div>
        </div>
        ${badge}
      </div>
    `;
  }).join('');
}

function renderCandidatesTable(data) {
  const tbody = document.getElementById('candidates-table-body');
  if (!tbody) return;

  const candidates = data.candidateComponents || [];
  // Show ranks 2 to 6 if top candidate displayed in hero card, or 1 to 5
  const alts = candidates.length > 1 ? candidates.slice(1, 6) : candidates;

  if (alts.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="py-4 text-center text-slate-500 text-xs">
          No alternative candidate components mapped to this specification.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = alts.map((c, idx) => {
    const rank = candidates.length > 1 ? idx + 2 : idx + 1;
    const q = c.fingerprintQuality || 'MED';
    const score = c.confidence || Math.round((c.compatibility || 0) * 100);

    return `
      <tr class="hover:bg-slate-50 transition-colors">
        <td class="py-2.5 px-4 font-mono-code font-bold text-slate-500">#${rank}</td>
        <td class="py-2.5 px-4 font-semibold text-slate-900">
          <button type="button" onclick='openComponentDetailModal(${JSON.stringify(c)})' class="hover:underline text-left text-slate-900 hover:text-[#ED0007]">
            ${c.name}
          </button>
        </td>
        <td class="py-2.5 px-4">
          <span class="px-2 py-0.5 rounded text-[10px] font-mono-code font-bold bg-slate-100 text-slate-700 border border-slate-200">
            ${q} Quality
          </span>
        </td>
        <td class="py-2.5 px-4 text-right font-mono-code text-slate-600">${c.sampleCount || 0}</td>
        <td class="py-2.5 px-4 text-right font-mono-code font-bold text-slate-900">${score}%</td>
        <td class="py-2.5 px-4 text-slate-500 text-[11px] truncate max-w-xs">${c.notes || 'Reference fingerprint'}</td>
      </tr>
    `;
  }).join('');
}

function renderWarningsAndConflicts(data) {
  const card = document.getElementById('warnings-conflicts-card');
  const list = document.getElementById('warnings-list');
  if (!card || !list) return;

  const warnings = [];

  // Check declared material conflict
  if (data.conflict && data.conflict.has_conflict) {
    warnings.push({
      title: 'Declared Material Conflict Detected',
      message: data.conflict.message || `Declared metadata '${data.conflict.declared_material}' conflicts with measured EDS family '${data.conflict.predicted_family}'.`,
      severity: 'high',
      suggested: data.conflict.suggested_action || 'Inspect physical sample markings or verify whether surface plating is present.'
    });
  }

  // Low confidence warning
  if (data.compatibilityPct < 60) {
    warnings.push({
      title: 'Marginal Compatibility Fit',
      message: `Compatibility score (${data.compatibilityPct}%) is below nominal confidence threshold (60%).`,
      severity: 'medium',
      suggested: 'Consider rescanning particle or pooling additional spectra points.'
    });
  }

  // System caveats
  if (data.caveats && data.caveats.length > 0) {
    data.caveats.forEach(c => {
      warnings.push({
        title: 'Analytical Caveat',
        message: c,
        severity: 'info',
      });
    });
  }

  if (warnings.length === 0) {
    card.classList.add('hidden');
    list.innerHTML = '';
    return;
  }

  card.classList.remove('hidden');
  list.innerHTML = warnings.map(w => `
    <div class="p-3 bg-rose-50/50 border border-rose-200 rounded">
      <div class="font-bold text-rose-900 flex items-center gap-1.5">
        <span class="material-symbols-outlined text-[16px] text-rose-600">error</span>
        ${w.title}
      </div>
      <p class="text-slate-700 mt-1">${w.message}</p>
      ${w.suggested ? `<p class="text-[11px] text-rose-700 mt-1 italic font-medium">Recommended: ${w.suggested}</p>` : ''}
    </div>
  `).join('');
}

/* =========================================================================
   Inspection & Feedback Actions
   ========================================================================= */

function inspectTopComponent() {
  if (currentTopCandidate) {
    openComponentDetailModal(currentTopCandidate);
  }
}
window.inspectTopComponent = inspectTopComponent;

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
        title: comp.name,
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

/* Feedback submission */
async function confirmIdentification() {
  if (!currentPredictionData) {
    alert('No active prediction to confirm.');
    return;
  }

  const payload = {
    analysis_id: currentPredictionData.analysisId || null,
    spectrum: currentPredictionData.extractedComposition || {},
    predicted_family: currentPredictionData.materialFamily || 'Unknown',
    predicted_component: currentTopCandidate ? currentTopCandidate.name : null,
    confirmed_family: currentPredictionData.materialFamily || 'Unknown',
    confirmed_component: currentTopCandidate ? currentTopCandidate.name : 'Unknown',
    status: 'confirmed',
    analyst_name: 'Lead Metallurgist',
    notes: 'Analyst verified nominal EDS stoichiometry matches specification.',
  };

  try {
    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      alert('Analyst confirmation recorded successfully in the audit feedback loop.');
    } else {
      alert('Failed to save confirmation.');
    }
  } catch (err) {
    alert('Network error saving feedback.');
  }
}
window.confirmIdentification = confirmIdentification;

function openSuggestCorrectionModal() {
  if (!currentPredictionData) {
    alert('No active prediction to correct.');
    return;
  }

  const content = `
    <div class="space-y-4 text-xs">
      <div class="p-3 bg-slate-50 border border-slate-200 rounded">
        <div class="text-slate-500">Current Prediction:</div>
        <div class="font-bold text-slate-900 text-sm mt-0.5">${currentPredictionData.materialFamily}</div>
        <div class="text-slate-600 font-mono-code mt-0.5">Top Component: ${currentTopCandidate ? currentTopCandidate.name : 'None'}</div>
      </div>

      <div>
        <label class="block font-bold text-slate-700 mb-1">Corrected Material Family</label>
        <select id="modal-correct-family" class="w-full rounded border border-slate-300 p-2 bg-white text-slate-800">
          <option value="Plain / Low-Manganese Carbon Steel">Plain / Low-Manganese Carbon Steel (F1a)</option>
          <option value="~1.5% Manganese Carbon Steel">~1.5% Manganese Carbon Steel (F1b)</option>
          <option value="Silicon-Chromium Spring Steel">Silicon-Chromium Spring Steel (F1c)</option>
          <option value="Low-Alloy Chromium Bearing Steel (100Cr6)" selected>Low-Alloy Chromium Bearing Steel (100Cr6) (F2)</option>
          <option value="High-Speed Tool Steel (M2 / S6-5-2)">High-Speed Tool Steel (M2 / S6-5-2) (F3)</option>
          <option value="Austenitic Stainless Steel 18/8 (AISI 304)">Austenitic Stainless Steel 18/8 (AISI 304) (F4)</option>
          <option value="Nickel-Base Superalloy (Ni-Cr)">Nickel-Base Superalloy (Ni-Cr) (F5)</option>
          <option value="Copper-Tin Bronze (CuSn8)">Copper-Tin Bronze (CuSn8) (F6a)</option>
          <option value="Bimetallic Cu-Sn Bronze on Steel">Bimetallic Cu-Sn Bronze on Steel (F6b)</option>
          <option value="Gold-Plated Electrical Contact">Gold-Plated Electrical Contact (F7)</option>
          <option value="Zinc-Coated / Galvanized Steel">Zinc-Coated / Galvanized Steel (F8a)</option>
          <option value="Zinc-Phosphate Conversion Coated Steel">Zinc-Phosphate Conversion Coated Steel (F8b)</option>
        </select>
      </div>

      <div>
        <label class="block font-bold text-slate-700 mb-1">Corrected Component / Part Name</label>
        <input type="text" id="modal-correct-component" placeholder="e.g. Armature Bolt, CRI Sealing Ring..." class="w-full rounded border border-slate-300 p-2 bg-white text-slate-800">
      </div>

      <div>
        <label class="block font-bold text-slate-700 mb-1">Metallurgical Notes / Rationale</label>
        <textarea id="modal-correct-notes" rows="3" placeholder="Provide reason for correction (e.g. surface plating interference, known part assembly)..." class="w-full rounded border border-slate-300 p-2 bg-white text-slate-800"></textarea>
      </div>
    </div>
  `;

  const actions = `
    <button type="button" onclick="submitCorrectionFeedback()" class="px-4 py-2 text-xs font-bold rounded bg-[#ED0007] text-white hover:bg-[#c90006]">
      Submit Correction
    </button>
    <button type="button" onclick="window.closeAppModal()" class="px-4 py-2 text-xs font-semibold rounded bg-white text-slate-700 border border-slate-300 hover:bg-slate-50">
      Cancel
    </button>
  `;

  window.openAppModal({
    title: 'Suggest Metallurgical Correction',
    subtitle: 'Feedback loop audit log',
    contentHtml: content,
    actionsHtml: actions,
  });
}
window.openSuggestCorrectionModal = openSuggestCorrectionModal;

async function submitCorrectionFeedback() {
  const fam = document.getElementById('modal-correct-family').value;
  const comp = document.getElementById('modal-correct-component').value.trim() || 'Custom Component';
  const notes = document.getElementById('modal-correct-notes').value.trim();

  const payload = {
    analysis_id: currentPredictionData.analysisId || null,
    spectrum: currentPredictionData.extractedComposition || {},
    predicted_family: currentPredictionData.materialFamily || 'Unknown',
    predicted_component: currentTopCandidate ? currentTopCandidate.name : null,
    confirmed_family: fam,
    confirmed_component: comp,
    status: 'corrected',
    analyst_name: 'Lead Metallurgist',
    notes: notes,
  };

  try {
    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      window.closeAppModal();
      alert('Correction logged successfully to the feedback training dataset.');
    } else {
      alert('Failed to submit correction.');
    }
  } catch (err) {
    alert('Network error submitting feedback.');
  }
}
window.submitCorrectionFeedback = submitCorrectionFeedback;
