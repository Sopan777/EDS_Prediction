/**
 * static/js/analyzer.js
 * =====================
 * Interactive controller for Analyzer screen (drag-and-drop, multi-spectrum
 * particle pooling, elemental wt% entry, presets, top component prediction,
 * and ASTM / ISO compliant metallurgical cross-correlation).
 */

let spectraListState = [
  { Cr: 0, Ni: 0, Mn: 0, Si: 0, Fe: 'Bal.', extras: {} }
];
let activeSpectrumIdx = 0;
let extraElementsState = {};
let uploadedFileState = null;
let currentTopCandidate = null;

function switchIngestTab(tab) {
  const btnUpload = document.getElementById('tab-btn-upload');
  const btnManual = document.getElementById('tab-btn-manual');
  const uploadSection = document.getElementById('section-file-upload');

  if (tab === 'upload') {
    uploadSection.classList.remove('hidden');
    btnUpload.className = 'px-3 py-1 rounded-md text-[11px] font-bold uppercase tracking-wider transition-all bg-white text-[#134231] dark:bg-[#1a2420] dark:text-[#00ffcc] shadow-sm';
    btnManual.className = 'px-3 py-1 rounded-md text-[11px] font-bold uppercase tracking-wider transition-all text-[#717974] hover:text-[#191c1e] dark:text-[#83958d] dark:hover:text-white';
  } else {
    uploadSection.classList.add('hidden');
    btnManual.className = 'px-3 py-1 rounded-md text-[11px] font-bold uppercase tracking-wider transition-all bg-white text-[#134231] dark:bg-[#1a2420] dark:text-[#00ffcc] shadow-sm';
    btnUpload.className = 'px-3 py-1 rounded-md text-[11px] font-bold uppercase tracking-wider transition-all text-[#717974] hover:text-[#191c1e] dark:text-[#83958d] dark:hover:text-white';
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
        dropZone.classList.add('border-emerald-500', 'bg-emerald-50/10');
      });
    });

    ['dragleave', 'drop'].forEach(name => {
      dropZone.addEventListener(name, (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-emerald-500', 'bg-emerald-50/10');
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
   Multi-Spectrum State Management
   ========================================================================= */

function renderSpectrumTabs() {
  const container = document.getElementById('spectrum-tabs-bar');
  if (!container) return;

  container.innerHTML = spectraListState.map((spec, idx) => {
    const isActive = idx === activeSpectrumIdx;
    const activeClass = 'px-2.5 py-1 text-[11px] font-bold rounded-md transition-all bg-[#134231] text-white dark:bg-[#00ffcc] dark:text-[#00382b] shadow-sm';
    const inactiveClass = 'px-2.5 py-1 text-[11px] font-medium rounded-md transition-all border border-[#c0c8c2] bg-[#f7f9fb] text-[#414944] hover:text-[#191c1e] hover:bg-[#eceef0] dark:border-[#3a4a44] dark:bg-[#151d1a] dark:text-[#83958d] dark:hover:text-white';

    return `
      <button type="button" onclick="switchSpectrumTab(${idx})" class="${isActive ? activeClass : inactiveClass}">
        Spectrum ${idx + 1}
      </button>
    `;
  }).join('');

  // Active badge label
  const badge = document.getElementById('active-spectrum-badge');
  if (badge) {
    const total = spectraListState.length;
    badge.textContent = total > 1
      ? `Editing: Spectrum ${activeSpectrumIdx + 1} of ${total}`
      : `Spectrum 1`;
  }

  // Delete button visibility
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
  // Clone current extra keys with 0 values for convenience
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

function handleFileSelected(file) {
  if (!file) return;
  uploadedFileState = file;

  const statusText = document.getElementById('upload-status-text');
  if (statusText) {
    statusText.innerHTML = `Loaded: <strong class="text-emerald-500">${file.name}</strong> (${(file.size / 1024).toFixed(1)} KB)`;
  }

  // Automatically analyze on upload
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

  // Extra elements
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
    <div class="relative group">
      <div class="flex justify-between items-center mb-1">
        <label class="text-[11px] font-bold uppercase tracking-wider text-emerald-500">${elem}</label>
        <button type="button" onclick="removeExtraElement('${elem}')" class="text-[11px] text-rose-500 hover:text-rose-700 opacity-0 group-hover:opacity-100 transition-opacity" title="Remove">✕</button>
      </div>
      <input type="number" step="0.01" value="${extraElementsState[elem]}" onchange="extraElementsState['${elem}'] = parseFloat(this.value)||0; syncCurrentSpectrumFromInputs();" class="w-full border rounded p-2 text-right font-mono-code text-[13px] font-medium bg-[#f7f9fb] border-emerald-500/40 dark:bg-[#151d1a] dark:border-[#00ffcc]/40 dark:text-white focus:outline-none">
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

  document.getElementById('awaiting-analysis-card').classList.remove('hidden');
  document.getElementById('analysis-results-card').classList.add('hidden');
  document.getElementById('btn-reset-analysis').classList.add('hidden');
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

  btn.disabled = true;
  btnText.textContent = 'Analyzing Spectrums...';
  spinner.classList.remove('hidden');

  const start = performance.now();

  try {
    let res;
    if (uploadedFileState) {
      const fd = new FormData();
      fd.append('file', uploadedFileState);
      res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken() },
        body: fd,
      });
    } else {
      syncCurrentSpectrumFromInputs();

      // Compile spectra array
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

      // Verify that at least one spectrum has non-zero inputs
      const hasData = spectraPayload.some(s => {
        return (s.Cr || 0) + (s.Ni || 0) + (s.Mn || 0) + (s.Si || 0) +
          Object.entries(s).filter(([k]) => !['Cr', 'Ni', 'Mn', 'Si', 'Fe', 'C'].includes(k)).reduce((acc, [, v]) => acc + (typeof v === 'number' ? v : 0), 0) > 0;
      });

      if (!hasData) {
        alert('Please enter elemental concentrations (wt%) or upload an EDS report to perform microanalysis.');
        return;
      }

      res = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({ spectra: spectraPayload }),
      });
    }

    const data = await res.json();
    if (!res.ok) {
      alert(data.error || 'Prediction failed');
      return;
    }

    // Populate extracted multi-spectrum data back into tabs for user inspection
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
    } else if (data.extractedComposition) {
      const ext = data.extractedComposition;
      document.getElementById('input-cr').value = ext.Cr || 0;
      document.getElementById('input-ni').value = ext.Ni || 0;
      document.getElementById('input-mn').value = ext.Mn || 0;
      document.getElementById('input-si').value = ext.Si || 0;
      document.getElementById('input-fe').value = ext.Fe !== undefined ? `${ext.Fe}%` : 'Bal.';

      const extras = {};
      for (const [k, v] of Object.entries(ext)) {
        if (!['Cr', 'Ni', 'Mn', 'Si', 'Fe', 'C'].includes(k) && typeof v === 'number') {
          extras[k] = v;
        }
      }
      extraElementsState = extras;
      renderExtraElements();
      syncCurrentSpectrumFromInputs();
    }

    renderPredictionResults(data, ((performance.now() - start) / 1000).toFixed(2));
  } catch (err) {
    console.error('Analysis error:', err);
    alert('Connection error communicating with EDS analysis API.');
  } finally {
    btn.disabled = false;
    btnText.textContent = 'Predict Family & Component';
    spinner.classList.add('hidden');
  }
}

/* =========================================================================
   Results Rendering
   ========================================================================= */

function formatCompositionSummary(comp) {
  if (!comp) return '';
  const entries = Object.entries(comp)
    .filter(([k, v]) => typeof v === 'number' && v > 0.05)
    .sort((a, b) => b[1] - a[1]);
  return entries.slice(0, 4).map(([k, v]) => `${k} ${v.toFixed(1)}%`).join(', ');
}

function renderPredictionResults(data, elapsedSecs) {
  document.getElementById('awaiting-analysis-card').classList.add('hidden');
  document.getElementById('analysis-results-card').classList.remove('hidden');
  document.getElementById('btn-reset-analysis').classList.remove('hidden');

  // Timer
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
  if (data.decision === 'identified') {
    badge.className = 'inline-flex items-center gap-1.5 bg-[#bcedd4] text-[#002115] px-2.5 py-1 rounded-full text-[11px] font-bold tracking-wider border border-[#a1d1b9]';
    badge.innerHTML = '<span class="material-symbols-outlined text-[14px]">check_circle</span> IDENTIFIED';
  } else if (data.decision === 'ambiguous') {
    badge.className = 'inline-flex items-center gap-1.5 bg-[#fef3c7] text-[#92400e] px-2.5 py-1 rounded-full text-[11px] font-bold tracking-wider border border-[#fde68a]';
    badge.innerHTML = '<span class="material-symbols-outlined text-[14px]">help</span> AMBIGUOUS SET';
  } else {
    badge.className = 'inline-flex items-center gap-1.5 bg-[#fee2e2] text-[#991b1b] px-2.5 py-1 rounded-full text-[11px] font-bold tracking-wider border border-[#fecaca]';
    badge.innerHTML = '<span class="material-symbols-outlined text-[14px]">cancel</span> UNKNOWN / ABSTAINED';
  }

  // Material Title & Hint
  const titleEl = document.getElementById('result-material-title');
  const hintEl = document.getElementById('result-grade-hint');

  if (data.decision === 'unknown') {
    titleEl.textContent = 'Unclassified Material';
    hintEl.innerHTML = `<span class="material-symbols-outlined text-[16px]">info</span> ${data.reason || 'Abstained: insufficient alloy signal for reliable specification check'}`;
  } else {
    titleEl.textContent = data.materialFamily;
    hintEl.innerHTML = `<span class="material-symbols-outlined text-[16px]">info</span> Grade hint: ${data.gradeHint || 'Reference standard'}${data.decision === 'ambiguous' ? ' (Tied candidate families)' : ''}`;
  }

  // Circular Gauge
  const pct = data.compatibilityPct || 0;
  const strokeEl = document.getElementById('gauge-stroke-path');
  const pctText = document.getElementById('gauge-pct-text');
  const gaugeTitle = document.getElementById('gauge-title-text');
  const gaugeDesc = document.getElementById('gauge-desc-text');

  strokeEl.setAttribute('stroke-dasharray', `${pct}, 100`);
  pctText.textContent = `${pct}%`;

  if (data.decision === 'unknown') {
    strokeEl.className = 'text-rose-500';
    pctText.className = 'font-mono-code font-bold text-[13px] text-rose-500';
    gaugeTitle.textContent = 'Abstained by Rule Engine';
    gaugeDesc.textContent = data.reason || 'Measurement did not exhibit decisive alloy markers. Safe abstention prevents misclassification.';
  } else if (data.decision === 'ambiguous') {
    strokeEl.className = 'text-amber-500';
    pctText.className = 'font-mono-code font-bold text-[13px] text-amber-500';
    gaugeTitle.textContent = 'Ambiguous Spectral Fit';
    gaugeDesc.textContent = 'Observed stoichiometry is consistent with multiple material families within measurement error.';
  } else {
    strokeEl.className = 'text-[#134231] dark:text-[#00ffcc]';
    pctText.className = 'font-mono-code font-bold text-[13px] text-[#134231] dark:text-[#00ffcc]';
    gaugeTitle.textContent = 'High Compatibility';
    const pooledPrefix = data.isPooled ? `Pooled average across ${data.spectraCount} spectra ` : 'Spectral signature ';
    gaugeDesc.textContent = `${pooledPrefix}closely matches reference library standards for ${data.familyCode || 'sample'} (${data.gradeHint || ''}).`;
  }

  // Top Predicted Component Card
  currentTopCandidate = data.topCandidate || (data.candidateComponents && data.candidateComponents[0]) || null;
  const topCompCard = document.getElementById('top-predicted-component-card');

  if (currentTopCandidate && topCompCard) {
    topCompCard.classList.remove('hidden');
    document.getElementById('top-comp-name').textContent = currentTopCandidate.name;
    document.getElementById('top-comp-sub').textContent = `${currentTopCandidate.category || 'Precision System'} • Part #: ${currentTopCandidate.partNumber || 'BOSCH-EDS-REF'}`;
    document.getElementById('top-comp-alloy').textContent = currentTopCandidate.nominalAlloy || 'Standard Alloy';
    document.getElementById('top-comp-conf-badge').textContent = `${currentTopCandidate.confidence || 95}% Match`;

    const distEl = document.getElementById('top-comp-distance');
    if (distEl) {
      distEl.textContent = currentTopCandidate.distance !== undefined
        ? `Centroid Dist: ${currentTopCandidate.distance}`
        : `Centroid Match`;
    }

    const notesEl = document.getElementById('top-comp-notes');
    if (notesEl) {
      notesEl.textContent = currentTopCandidate.notes || 'Optimal metallurgical distance fit against reference database centroids.';
    }
  } else if (topCompCard) {
    topCompCard.classList.add('hidden');
  }

  // Multi-Spectra Inspector Card
  const inspectorCard = document.getElementById('multi-spectra-inspector-card');
  const inspectorList = document.getElementById('inspector-spectra-list');
  const inspectorCount = document.getElementById('inspector-spectra-count');

  if (data.isPooled && data.perSpectrum && data.perSpectrum.length > 1 && inspectorCard && inspectorList) {
    inspectorCard.classList.remove('hidden');
    inspectorCount.textContent = `${data.perSpectrum.length} Spectra Analyzed`;

    inspectorList.innerHTML = data.perSpectrum.map(s => `
      <div class="flex items-center justify-between p-2 rounded-lg border bg-[#f7f9fb] border-[#c0c8c2]/50 dark:bg-[#151d1a] dark:border-[#3a4a44]/50 text-[11.5px]">
        <div class="min-w-0 pr-2">
          <span class="font-bold text-[#134231] dark:text-[#00ffcc]">${s.label}:</span>
          <span class="font-mono-code ml-1 text-[#414944] dark:text-[#b9cbc2] truncate inline-block max-w-[220px] align-bottom">
            ${formatCompositionSummary(s.composition)}
          </span>
        </div>
        <div class="shrink-0 flex items-center gap-1.5 font-semibold text-[11px] text-emerald-600 dark:text-[#00ffcc]">
          <span>${s.family}</span>
          <span class="font-mono-code text-[10px] opacity-75">(${s.compatibilityPct}%)</span>
        </div>
      </div>
    `).join('');
  } else if (inspectorCard) {
    inspectorCard.classList.add('hidden');
  }

  // Other Candidate Components List
  const candList = document.getElementById('candidates-list');
  const allCandidates = data.candidateComponents || [];
  // If topCandidate is displayed in top card, show ranks 2..N, else show all
  const otherCandidates = (currentTopCandidate && allCandidates.length > 1)
    ? allCandidates.slice(1, 4)
    : allCandidates.slice(0, 3);

  if (otherCandidates.length === 0) {
    candList.innerHTML = `
      <div class="h-full flex flex-col items-center justify-center text-center p-3 opacity-60">
        <span class="material-symbols-outlined text-[24px] mb-1">category</span>
        <p class="text-[12px] font-semibold">No additional candidates mapped</p>
      </div>`;
  } else {
    candList.innerHTML = otherCandidates.map((comp, idx) => {
      const displayIdx = currentTopCandidate ? idx + 2 : idx + 1;
      return `
        <div onclick='openComponentModal(${JSON.stringify(comp)})' class="flex items-center justify-between p-2 rounded-lg border transition-all cursor-pointer group bg-[#f7f9fb] border-transparent hover:border-[#134231] hover:bg-[#f2f4f6] dark:bg-[#151d1a] dark:border-transparent dark:hover:border-[#00ffcc] dark:hover:bg-[#1a2420]">
          <div class="flex items-center gap-2">
            <span class="w-5 h-5 rounded-full flex items-center justify-center font-mono-code text-[10px] font-bold bg-[#eceef0] text-[#717974] dark:bg-[#232c28] dark:text-[#b9cbc2]">
              ${displayIdx}
            </span>
            <div class="min-w-0">
              <span class="font-semibold text-[12.5px] block truncate text-[#191c1e] dark:text-white group-hover:underline">${comp.name}</span>
              <span class="text-[10px] font-mono-code text-[#717974] dark:text-[#83958d]">${comp.partNumber} • ${comp.nominalAlloy}</span>
            </div>
          </div>
          <span class="material-symbols-outlined text-[16px] text-[#717974] dark:text-[#83958d] transition-transform group-hover:translate-x-0.5">chevron_right</span>
        </div>
      `;
    }).join('');
  }

  // Analysis Caveats
  const caveatsList = document.getElementById('caveats-list');
  const caveats = data.caveats || [];
  const defaultCaveats = [
    { title: 'Carbon untracked', description: 'C content not reliably determinable via standard EDS.', icon: 'warning' },
    { title: 'Renormalized', description: 'Metal-basis renormalized excluding O, C, N, F.', icon: 'calculate' },
  ];
  if (data.isPooled) {
    defaultCaveats.unshift({
      title: 'Multi-Spectrum Pooled',
      description: `Compositions pooled across ${data.spectraCount} spectra (particle centroid estimation).`,
      icon: 'layers',
    });
  }
  const allCaveats = [...defaultCaveats, ...caveats.map(c => ({ title: 'System Note', description: c, icon: 'info' }))];

  caveatsList.innerHTML = allCaveats.map(c => `
    <div class="p-2 rounded border flex gap-2 items-start bg-[#f7f9fb] border-[#c0c8c2]/50 dark:bg-[#151d1a] dark:border-[#3a4a44]/50">
      <span class="material-symbols-outlined text-[15px] mt-0.5 shrink-0 text-[#717974] dark:text-[#00ffcc]">${c.icon}</span>
      <div>
        <span class="block font-semibold text-[11.5px] text-[#191c1e] dark:text-white">${c.title}</span>
        <span class="block text-[10.5px] leading-tight mt-0.5 text-[#717974] dark:text-[#b9cbc2]">${c.description}</span>
      </div>
    </div>
  `).join('');

  // Update Global Active Family reference for Export modal
  if (data.topFamily) {
    window.ACTIVE_FAMILY = data.topFamily;
  }
}

function inspectTopComponent() {
  if (currentTopCandidate && typeof openComponentModal === 'function') {
    openComponentModal(currentTopCandidate);
  }
}
window.inspectTopComponent = inspectTopComponent;
