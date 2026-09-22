/**
 * static/js/analyzer.js
 * =====================
 * Interactive controller for Analyzer screen (drag-and-drop, manual wt%,
 * presets, prediction execution, circular gauge rendering).
 */

let extraElementsState = {};
let uploadedFileState = null;

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

function handleFileSelected(file) {
  if (!file) return;
  uploadedFileState = file;

  const statusText = document.getElementById('upload-status-text');
  if (statusText) {
    statusText.innerHTML = `Loaded: <strong class="text-emerald-500">${file.name}</strong> (${(file.size / 1024).toFixed(1)} KB)`;
  }

  // Directly run extraction on upload
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
  }
}

function removeExtraElement(elem) {
  delete extraElementsState[elem];
  renderExtraElements();
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
      <input type="number" step="0.01" value="${extraElementsState[elem]}" onchange="extraElementsState['${elem}'] = parseFloat(this.value)||0" class="w-full border rounded p-2 text-right font-mono-code text-[13px] font-medium bg-[#f7f9fb] border-emerald-500/40 dark:bg-[#151d1a] dark:border-[#00ffcc]/40 dark:text-white focus:outline-none">
    </div>
  `).join('');
}

function clearAnalyzerForm() {
  uploadedFileState = null;
  extraElementsState = {};
  document.getElementById('input-cr').value = 0;
  document.getElementById('input-ni').value = 0;
  document.getElementById('input-mn').value = 0;
  document.getElementById('input-si').value = 0;
  document.getElementById('input-fe').value = 'Bal.';

  const fileInput = document.getElementById('eds-file-input');
  if (fileInput) fileInput.value = '';
  const statusText = document.getElementById('upload-status-text');
  if (statusText) statusText.textContent = 'Drag & Drop EDS Report or Click to Browse';

  renderExtraElements();

  document.getElementById('awaiting-analysis-card').classList.remove('hidden');
  document.getElementById('analysis-results-card').classList.add('hidden');
  document.getElementById('btn-reset-analysis').classList.add('hidden');
}
window.clearAnalyzerForm = clearAnalyzerForm;

async function triggerPrediction() {
  const btn = document.getElementById('btn-predict-family');
  const btnText = document.getElementById('predict-btn-text');
  const spinner = document.getElementById('predict-btn-spinner');

  btn.disabled = true;
  btnText.textContent = 'Correlating Spectra...';
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
      const cr = parseFloat(document.getElementById('input-cr').value) || 0;
      const ni = parseFloat(document.getElementById('input-ni').value) || 0;
      const mn = parseFloat(document.getElementById('input-mn').value) || 0;
      const si = parseFloat(document.getElementById('input-si').value) || 0;
      const fe = document.getElementById('input-fe').value || 'Bal.';

      const total = cr + ni + mn + si + Object.values(extraElementsState).reduce((a, b) => a + b, 0);
      if (total === 0) {
        alert('Please enter elemental concentrations (wt%) or upload an EDS report to perform microanalysis.');
        return;
      }

      const payload = {
        composition: {
          Cr: cr,
          Ni: ni,
          Mn: mn,
          Si: si,
          Fe: fe,
          ...extraElementsState,
        },
      };

      res = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify(payload),
      });
    }

    const data = await res.json();
    if (!res.ok) {
      alert(data.error || 'Prediction failed');
      return;
    }

    // Populate extracted values if available
    if (data.extractedComposition) {
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
    }

    renderPredictionResults(data, ((performance.now() - start) / 1000).toFixed(2));
  } catch (err) {
    console.error('Analysis error:', err);
    alert('Connection error communicating with EDS analysis API.');
  } finally {
    btn.disabled = false;
    btnText.textContent = 'Predict Family';
    spinner.classList.add('hidden');
  }
}

function renderPredictionResults(data, elapsedSecs) {
  document.getElementById('awaiting-analysis-card').classList.add('hidden');
  document.getElementById('analysis-results-card').classList.remove('hidden');
  document.getElementById('btn-reset-analysis').classList.remove('hidden');

  // Timer
  document.getElementById('result-duration').textContent = data.processingTime || `${elapsedSecs}s`;

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
    pctText.className = 'font-mono-code font-bold text-[14px] text-rose-500';
    gaugeTitle.textContent = 'Abstained by Rule Engine';
    gaugeDesc.textContent = data.reason || 'Measurement did not exhibit decisive alloy markers. Safe abstention prevents misclassification.';
  } else if (data.decision === 'ambiguous') {
    strokeEl.className = 'text-amber-500';
    pctText.className = 'font-mono-code font-bold text-[14px] text-amber-500';
    gaugeTitle.textContent = 'Ambiguous Spectral Fit';
    gaugeDesc.textContent = 'Observed stoichiometry is consistent with multiple material families within measurement error.';
  } else {
    strokeEl.className = 'text-[#134231] dark:text-[#00ffcc]';
    pctText.className = 'font-mono-code font-bold text-[14px] text-[#134231] dark:text-[#00ffcc]';
    gaugeTitle.textContent = 'High Compatibility';
    gaugeDesc.textContent = `Spectral signature closely matches reference library standards for ${data.familyCode || 'sample'} (${data.gradeHint || ''}).`;
  }

  // Candidate Components
  const candList = document.getElementById('candidates-list');
  const candidates = data.candidateComponents || [];
  if (candidates.length === 0) {
    candList.innerHTML = `
      <div class="h-full flex flex-col items-center justify-center text-center p-3 opacity-60">
        <span class="material-symbols-outlined text-[26px] mb-1">category</span>
        <p class="text-[12px] font-semibold">No candidate components mapped</p>
      </div>`;
  } else {
    candList.innerHTML = candidates.slice(0, 3).map((comp, idx) => `
      <div onclick='openComponentModal(${JSON.stringify(comp)})' class="flex items-center justify-between p-2 rounded-lg border transition-all cursor-pointer group bg-[#f7f9fb] border-transparent hover:border-[#134231] hover:bg-[#f2f4f6] dark:bg-[#151d1a] dark:border-transparent dark:hover:border-[#00ffcc] dark:hover:bg-[#1a2420]">
        <div class="flex items-center gap-2.5">
          <span class="w-6 h-6 rounded-full flex items-center justify-center font-mono-code text-[11px] font-bold ${idx === 0 ? 'bg-[#134231] text-white dark:bg-[#00ffcc] dark:text-[#00382b]' : 'bg-[#eceef0] text-[#717974] dark:bg-[#232c28] dark:text-[#b9cbc2]'}">
            ${idx + 1}
          </span>
          <div class="min-w-0">
            <span class="font-semibold text-[13px] block truncate text-[#191c1e] dark:text-white group-hover:underline">${comp.name}</span>
            <span class="text-[10px] font-mono-code text-[#717974] dark:text-[#83958d]">${comp.partNumber} • ${comp.nominalAlloy}</span>
          </div>
        </div>
        <span class="material-symbols-outlined text-[18px] text-[#717974] dark:text-[#83958d] transition-transform group-hover:translate-x-0.5">chevron_right</span>
      </div>
    `).join('');
  }

  // Analysis Caveats
  const caveatsList = document.getElementById('caveats-list');
  const caveats = data.caveats || [];
  const defaultCaveats = [
    { title: 'Carbon untracked', description: 'C content not reliably determinable via standard EDS.', icon: 'warning' },
    { title: 'Renormalized', description: 'Metal-basis renormalized excluding O, C, N, F.', icon: 'calculate' },
  ];
  const allCaveats = [...defaultCaveats, ...caveats.map(c => ({ title: 'System Note', description: c, icon: 'info' }))];

  caveatsList.innerHTML = allCaveats.map(c => `
    <div class="p-2 rounded border flex gap-2 items-start bg-[#f7f9fb] border-[#c0c8c2]/50 dark:bg-[#151d1a] dark:border-[#3a4a44]/50">
      <span class="material-symbols-outlined text-[16px] mt-0.5 shrink-0 text-[#717974] dark:text-[#00ffcc]">${c.icon}</span>
      <div>
        <span class="block font-semibold text-[12px] text-[#191c1e] dark:text-white">${c.title}</span>
        <span class="block text-[11px] leading-tight mt-0.5 text-[#717974] dark:text-[#b9cbc2]">${c.description}</span>
      </div>
    </div>
  `).join('');

  // Update Global Active Family reference for Export modal
  if (data.topFamily) {
    window.ACTIVE_FAMILY = data.topFamily;
  }
}
