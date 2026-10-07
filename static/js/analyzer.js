/**
 * static/js/analyzer.js
 * =====================
 * Controller for DHATU BODH EDS Analyzer screen.
 * Handles single-card switchable Drag & Drop File (default) and Manual Elements
 * (dataset-driven element list) modes, wt%/at% conversion, Fe auto-balancing,
 * multi-spectrum pooling, and prioritized metallurgical results display.
 */

// Dataset-supported elements injected from Excel dataset headers (never the full periodic table)
const DEFAULT_DATASET_ELEMENTS = [
  { symbol: 'Fe', name: 'Iron', atomic_weight: 55.845 },
  { symbol: 'Cr', name: 'Chromium', atomic_weight: 51.996 },
  { symbol: 'Ni', name: 'Nickel', atomic_weight: 58.693 },
  { symbol: 'Mn', name: 'Manganese', atomic_weight: 54.938 },
  { symbol: 'Si', name: 'Silicon', atomic_weight: 28.085 },
  { symbol: 'C', name: 'Carbon', atomic_weight: 12.011 },
  { symbol: 'Mo', name: 'Molybdenum', atomic_weight: 95.95 },
  { symbol: 'Cu', name: 'Copper', atomic_weight: 63.546 },
  { symbol: 'Sn', name: 'Tin', atomic_weight: 118.71 },
  { symbol: 'Al', name: 'Aluminium', atomic_weight: 26.982 },
  { symbol: 'Zn', name: 'Zinc', atomic_weight: 65.38 },
  { symbol: 'W', name: 'Tungsten', atomic_weight: 183.84 },
  { symbol: 'V', name: 'Vanadium', atomic_weight: 50.942 },
  { symbol: 'Ti', name: 'Titanium', atomic_weight: 47.867 },
  { symbol: 'Nb', name: 'Niobium', atomic_weight: 92.906 },
  { symbol: 'Co', name: 'Cobalt', atomic_weight: 58.933 },
  { symbol: 'N', name: 'Nitrogen', atomic_weight: 14.007 },
  { symbol: 'O', name: 'Oxygen', atomic_weight: 15.999 },
  { symbol: 'P', name: 'Phosphorus', atomic_weight: 30.974 },
  { symbol: 'S', name: 'Sulfur', atomic_weight: 32.06 },
  { symbol: 'Pb', name: 'Lead', atomic_weight: 207.2 },
  { symbol: 'Au', name: 'Gold', atomic_weight: 196.967 },
];

function getDatasetElements() {
  if (Array.isArray(window.DATASET_ELEMENTS) && window.DATASET_ELEMENTS.length > 0) {
    return window.DATASET_ELEMENTS;
  }
  return DEFAULT_DATASET_ELEMENTS;
}

function getAtomicWeight(sym) {
  const found = getDatasetElements().find(e => e.symbol === sym);
  return found && found.atomic_weight ? found.atomic_weight : 55.845;
}

// State: each spectrum stores an ordered list of selected elements and their values
let currentIngestMode = 'upload'; // 'upload' (default) | 'manual'
let currentConcentrationUnit = 'wt%'; // 'wt%' | 'at%'
let elementSearchQuery = '';

let spectraListState = [
  {
    selectedOrder: ['Fe', 'Ni', 'V'],
    values: { Fe: 'Bal.', Ni: 0, V: 0 },
  }
];
let activeSpectrumIdx = 0;
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

/* =========================================================================
   Mode Switching: [ Drag & Drop File ] vs [ Manual Elements ] in Single Card
   ========================================================================= */

function switchIngestTab(tab) {
  currentIngestMode = tab === 'manual' ? 'manual' : 'upload';
  const btnUpload = document.getElementById('tab-btn-upload');
  const btnManual = document.getElementById('tab-btn-manual');
  const uploadSection = document.getElementById('section-file-upload');
  const manualSection = document.getElementById('section-manual-elements');

  if (currentIngestMode === 'upload') {
    if (uploadSection) uploadSection.classList.remove('hidden');
    if (manualSection) manualSection.classList.add('hidden');
    if (btnUpload) btnUpload.className = 'ingest-mode-tab is-active';
    if (btnManual) btnManual.className = 'ingest-mode-tab';
  } else {
    if (uploadSection) uploadSection.classList.add('hidden');
    if (manualSection) manualSection.classList.remove('hidden');
    if (btnUpload) btnUpload.className = 'ingest-mode-tab';
    if (btnManual) btnManual.className = 'ingest-mode-tab is-active';
    renderManualElementsUI();
  }
}
window.switchIngestTab = switchIngestTab;

/* =========================================================================
   wt% / at% Unit Toggle & Stoichiometric Conversion
   ========================================================================= */

function setConcentrationUnit(unit) {
  if (unit !== 'wt%' && unit !== 'at%') return;
  if (unit === currentConcentrationUnit) return;

  const prevUnit = currentConcentrationUnit;
  currentConcentrationUnit = unit;

  const btnWt = document.getElementById('unit-btn-wt');
  const btnAt = document.getElementById('unit-btn-at');
  const unitLabel = document.getElementById('concentration-unit-label');

  if (unit === 'wt%') {
    if (btnWt) btnWt.className = 'unit-toggle-btn is-active';
    if (btnAt) btnAt.className = 'unit-toggle-btn';
  } else {
    if (btnAt) btnAt.className = 'unit-toggle-btn is-active';
    if (btnWt) btnWt.className = 'unit-toggle-btn';
  }
  if (unitLabel) unitLabel.textContent = unit;

  // Convert existing numeric concentrations in spectraListState
  spectraListState.forEach(spec => {
    spec.values = convertSpectrumUnits(spec.values, prevUnit, unit);
  });

  renderSelectedElementInputs();
}
window.setConcentrationUnit = setConcentrationUnit;

function convertSpectrumUnits(valuesObj, fromUnit, toUnit) {
  if (fromUnit === toUnit) return { ...valuesObj };
  const result = { ...valuesObj };
  const numericEntries = [];
  let sumNumeric = 0;
  let hasFeBalance = false;

  for (const [sym, val] of Object.entries(valuesObj)) {
    if (sym === 'Fe' && String(val).toLowerCase().startsWith('bal')) {
      hasFeBalance = true;
      continue;
    }
    const num = parseFloat(val);
    if (!isNaN(num) && num > 0) {
      numericEntries.push([sym, num]);
      sumNumeric += num;
    }
  }

  if (numericEntries.length === 0) return result;
  if (hasFeBalance && sumNumeric < 100) {
    numericEntries.push(['Fe', Math.max(0, 100 - sumNumeric)]);
  }

  if (fromUnit === 'wt%' && toUnit === 'at%') {
    // moles_i = wt_i / AW_i
    const moles = numericEntries.map(([sym, wt]) => [sym, wt / getAtomicWeight(sym)]);
    const totalMoles = moles.reduce((acc, [, m]) => acc + m, 0);
    if (totalMoles > 0) {
      moles.forEach(([sym, m]) => {
        if (sym === 'Fe' && hasFeBalance) {
          result[sym] = 'Bal.';
        } else {
          result[sym] = Math.round(((m / totalMoles) * 100) * 100) / 100;
        }
      });
    }
  } else if (fromUnit === 'at%' && toUnit === 'wt%') {
    // mass_i = at_i * AW_i
    const masses = numericEntries.map(([sym, at]) => [sym, at * getAtomicWeight(sym)]);
    const totalMass = masses.reduce((acc, [, m]) => acc + m, 0);
    if (totalMass > 0) {
      masses.forEach(([sym, m]) => {
        if (sym === 'Fe' && hasFeBalance) {
          result[sym] = 'Bal.';
        } else {
          result[sym] = Math.round(((m / totalMass) * 100) * 100) / 100;
        }
      });
    }
  }

  return result;
}

/* =========================================================================
   Initialization & Drag-and-Drop Setup
   ========================================================================= */

document.addEventListener('DOMContentLoaded', () => {
  // Default on page load: Drag & Drop File mode
  switchIngestTab('upload');
  renderManualElementsUI();

  const dropZone = document.getElementById('drop-zone');
  if (dropZone) {
    ['dragenter', 'dragover'].forEach(name => {
      dropZone.addEventListener(name, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add('is-dragover');
      });
    });

    ['dragleave', 'drop'].forEach(name => {
      dropZone.addEventListener(name, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('is-dragover');
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
   Manual Elements Mode: Dataset-Driven Element Grid & Concentration Inputs
   ========================================================================= */

function getActiveSpectrum() {
  if (!spectraListState[activeSpectrumIdx]) {
    spectraListState[activeSpectrumIdx] = {
      selectedOrder: ['Fe'],
      values: { Fe: 'Bal.' },
    };
  }
  return spectraListState[activeSpectrumIdx];
}

function renderManualElementsUI() {
  renderSpectrumTabs();
  renderSelectableElementsGrid();
  renderSelectedElementInputs();
  updateUnselectedElementsHint();
}

function filterSelectableElements(query) {
  elementSearchQuery = (query || '').trim().toLowerCase();
  renderSelectableElementsGrid();
}
window.filterSelectableElements = filterSelectableElements;

function renderSelectableElementsGrid() {
  const grid = document.getElementById('selectable-elements-grid');
  if (!grid) return;

  const activeSpec = getActiveSpectrum();
  const selectedSet = new Set(activeSpec.selectedOrder);
  const allElements = getDatasetElements();

  const filtered = allElements.filter(item => {
    if (!elementSearchQuery) return true;
    return (
      item.symbol.toLowerCase().includes(elementSearchQuery) ||
      (item.name && item.name.toLowerCase().includes(elementSearchQuery))
    );
  });

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="col-span-full py-3 text-center text-xs text-slate-400">
        No dataset element matches "${elementSearchQuery}".
      </div>
    `;
    return;
  }

  grid.innerHTML = filtered.map(item => {
    const sym = item.symbol;
    const isSelected = selectedSet.has(sym);

    if (isSelected) {
      return `
        <button type="button" onclick="toggleElementSelection('${sym}')" title="${item.name} (${sym}) — Click to remove"
          class="eds-el-chip is-selected">
          <span>${sym}</span>
          <span class="eds-el-check">✓</span>
        </button>
      `;
    } else {
      return `
        <button type="button" onclick="toggleElementSelection('${sym}')" title="${item.name} (${sym}) — Click to select"
          class="eds-el-chip">
          <span>${sym}</span>
        </button>
      `;
    }
  }).join('');
}

function toggleElementSelection(sym) {
  const activeSpec = getActiveSpectrum();
  const idx = activeSpec.selectedOrder.indexOf(sym);

  if (idx >= 0) {
    activeSpec.selectedOrder.splice(idx, 1);
    delete activeSpec.values[sym];
  } else {
    activeSpec.selectedOrder.push(sym);
    activeSpec.values[sym] = sym === 'Fe' ? 'Bal.' : 0;
  }

  uploadedFileState = null; // Manual edit supersedes raw file upload
  renderSelectableElementsGrid();
  renderSelectedElementInputs();
  updateUnselectedElementsHint();
}
window.toggleElementSelection = toggleElementSelection;

function removeSelectedElement(sym) {
  const activeSpec = getActiveSpectrum();
  const idx = activeSpec.selectedOrder.indexOf(sym);
  if (idx >= 0) {
    activeSpec.selectedOrder.splice(idx, 1);
    delete activeSpec.values[sym];
    uploadedFileState = null;
    renderSelectableElementsGrid();
    renderSelectedElementInputs();
    updateUnselectedElementsHint();
  }
}
window.removeSelectedElement = removeSelectedElement;

function clearAllSelectedElements() {
  const activeSpec = getActiveSpectrum();
  activeSpec.selectedOrder = [];
  activeSpec.values = {};
  uploadedFileState = null;
  renderSelectableElementsGrid();
  renderSelectedElementInputs();
  updateUnselectedElementsHint();
}
window.clearAllSelectedElements = clearAllSelectedElements;

function updateElementConcentration(sym, rawValue) {
  const activeSpec = getActiveSpectrum();
  uploadedFileState = null;
  if (sym === 'Fe' && String(rawValue).trim().toLowerCase().startsWith('bal')) {
    activeSpec.values['Fe'] = 'Bal.';
  } else {
    const parsed = parseFloat(rawValue);
    activeSpec.values[sym] = isNaN(parsed) ? 0 : parsed;
  }
}
window.updateElementConcentration = updateElementConcentration;

function renderSelectedElementInputs() {
  const grid = document.getElementById('selected-elements-inputs-grid');
  if (!grid) return;

  const activeSpec = getActiveSpectrum();
  const cardsHtml = activeSpec.selectedOrder.map(sym => {
    const val = activeSpec.values[sym] !== undefined ? activeSpec.values[sym] : (sym === 'Fe' ? 'Bal.' : 0);
    const isFe = sym === 'Fe';

    if (isFe) {
      return `
        <div class="eds-conc-card">
          <div class="flex items-center justify-between mb-1.5">
            <label class="text-xs font-bold text-slate-800">${sym}</label>
            <div class="flex items-center gap-1.5">
              <button type="button" onclick="autoBalanceFe()" class="text-[10px] font-bold text-[#ED0007] hover:underline" title="Auto-balance Fe to 100%">
                Balance
              </button>
              <button type="button" onclick="removeSelectedElement('${sym}')" class="text-xs text-slate-400 hover:text-rose-600 font-bold leading-none" title="Remove ${sym}">
                ×
              </button>
            </div>
          </div>
          <input type="text" id="input-el-${sym}" value="${val}" placeholder="Bal."
            onchange="updateElementConcentration('${sym}', this.value)"
            class="w-full bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-right font-mono-code text-sm font-bold text-slate-900 focus:outline-none focus:border-slate-600">
        </div>
      `;
    }

    return `
      <div class="eds-conc-card">
        <div class="flex items-center justify-between mb-1.5">
          <label class="text-xs font-bold text-slate-800">${sym}</label>
          <button type="button" onclick="removeSelectedElement('${sym}')" class="text-xs text-slate-400 hover:text-rose-600 font-bold leading-none" title="Remove ${sym}">
            ×
          </button>
        </div>
        <input type="number" step="0.01" min="0" max="100" id="input-el-${sym}" value="${val}" placeholder="0"
          onchange="updateElementConcentration('${sym}', this.value)"
          class="w-full bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-right font-mono-code text-sm font-semibold text-slate-900 focus:outline-none focus:border-slate-600">
      </div>
    `;
  });

  // Append the "+ Add Element" card at the end of the concentration grid (matching screenshot)
  cardsHtml.push(`
    <button type="button" onclick="focusElementSearch()" class="eds-add-el-card">
      <span class="material-symbols-outlined text-[18px] text-slate-500">add_circle</span>
      <span>Add Element</span>
    </button>
  `);

  grid.innerHTML = cardsHtml.join('');
}

function updateUnselectedElementsHint() {
  const hintEl = document.getElementById('unselected-elements-hint');
  if (!hintEl) return;
  const activeSpec = getActiveSpectrum();
  const selectedSet = new Set(activeSpec.selectedOrder);
  const unselected = getDatasetElements()
    .map(e => e.symbol)
    .filter(sym => !selectedSet.has(sym));

  if (unselected.length === 0) {
    hintEl.textContent = 'All dataset elements selected';
  } else {
    const preview = unselected.slice(0, 10).join(', ');
    hintEl.textContent = `Add Element (${preview}${unselected.length > 10 ? ', ...' : ''})`;
  }
}

function focusElementSearch() {
  const searchInput = document.getElementById('element-search-input');
  if (searchInput) {
    searchInput.focus();
    searchInput.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}
window.focusElementSearch = focusElementSearch;

/* =========================================================================
   Multi-Spectrum Pooling Tabs & Fe Auto-Balance
   ========================================================================= */

function renderSpectrumTabs() {
  const container = document.getElementById('spectrum-tabs-bar');
  if (!container) return;

  container.innerHTML = spectraListState.map((spec, idx) => {
    const isActive = idx === activeSpectrumIdx;
    const activeClass = 'px-2.5 py-1 text-[11px] font-bold rounded-md bg-[#0F2537] text-white shadow-2xs transition-all';
    const inactiveClass = 'px-2.5 py-1 text-[11px] font-medium rounded-md border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 transition-all';

    return `
      <button type="button" onclick="switchSpectrumTab(${idx})" class="${isActive ? activeClass : inactiveClass}">
        Spectrum ${idx + 1}
      </button>
    `;
  }).join('');

  const delBtn = document.getElementById('btn-delete-spectrum');
  if (delBtn) {
    delBtn.classList.toggle('hidden', spectraListState.length <= 1);
  }
}

function switchSpectrumTab(idx) {
  if (idx === activeSpectrumIdx || !spectraListState[idx]) return;
  activeSpectrumIdx = idx;
  renderManualElementsUI();
}
window.switchSpectrumTab = switchSpectrumTab;

function addNewSpectrumTab() {
  const curr = getActiveSpectrum();
  const newOrder = [...curr.selectedOrder];
  const newValues = {};
  newOrder.forEach(sym => {
    newValues[sym] = sym === 'Fe' ? 'Bal.' : 0;
  });
  spectraListState.push({
    selectedOrder: newOrder,
    values: newValues,
  });
  activeSpectrumIdx = spectraListState.length - 1;
  renderManualElementsUI();
}
window.addNewSpectrumTab = addNewSpectrumTab;

function removeCurrentSpectrumTab() {
  if (spectraListState.length <= 1) return;
  spectraListState.splice(activeSpectrumIdx, 1);
  activeSpectrumIdx = Math.max(0, activeSpectrumIdx - 1);
  renderManualElementsUI();
}
window.removeCurrentSpectrumTab = removeCurrentSpectrumTab;

function autoBalanceFe() {
  const activeSpec = getActiveSpectrum();
  if (!activeSpec.selectedOrder.includes('Fe')) {
    activeSpec.selectedOrder.unshift('Fe');
  }

  let sumOthers = 0;
  for (const sym of activeSpec.selectedOrder) {
    if (sym === 'Fe') continue;
    const val = parseFloat(activeSpec.values[sym]);
    if (!isNaN(val) && val > 0) {
      sumOthers += val;
    }
  }

  const feRem = Math.max(0, Math.round((100 - sumOthers) * 100) / 100);
  activeSpec.values['Fe'] = feRem.toFixed(2);
  uploadedFileState = null;
  renderSelectableElementsGrid();
  renderSelectedElementInputs();
  updateUnselectedElementsHint();
}
window.autoBalanceFe = autoBalanceFe;

/* =========================================================================
   File Upload & Extraction (Drag & Drop Mode)
   ========================================================================= */

async function handleFileSelected(file) {
  if (!file) return;
  if (file.size > 10 * 1024 * 1024) {
    alert('File exceeds the maximum allowed size of 10 MB.');
    return;
  }

  uploadedFileState = file;

  const statusText = document.getElementById('upload-status-text');
  const subStatusText = document.getElementById('upload-substatus-text');
  if (statusText) {
    statusText.innerHTML = `Selected: <span class="text-blue-700">${file.name}</span>`;
  }
  if (subStatusText) {
    subStatusText.textContent = `File size: ${(file.size / 1024).toFixed(1)} KB — Extracting all spectra (ignoring Mean / Std. deviation / Min / Max)...`;
  }

  // Extract elemental composition from the uploaded Report/Excel/EDS file
  try {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch('/api/extract', {
      method: 'POST',
      headers: { 'X-CSRFToken': getCSRFToken() },
      body: fd,
    });
    const data = await res.json();
    if (!res.ok) {
      if (subStatusText) {
        subStatusText.innerHTML = `<span class="text-rose-600 font-semibold">${data.error || 'Could not extract EDS spectra from file.'}</span>`;
      }
      return;
    }

    // Populate spectraListState with the extracted spectra
    if (Array.isArray(data.spectra) && data.spectra.length > 0) {
      const detailsList = (data.metadata && Array.isArray(data.metadata.spectra_details))
        ? data.metadata.spectra_details
        : [];

      currentConcentrationUnit = 'wt%';
      setConcentrationUnit('wt%');
      spectraListState = data.spectra.map((specObj, idx) => {
        const order = Object.keys(specObj);
        const vals = {};
        order.forEach(sym => {
          vals[sym] = Math.round(parseFloat(specObj[sym]) * 100) / 100;
        });
        const det = detailsList[idx] || {};
        return {
          selectedOrder: order,
          values: vals,
          label: det.label || det.spectrum_id || `Spectrum ${idx + 1}`,
          siteName: det.site_name || '',
          page: det.page || null,
        };
      });
      activeSpectrumIdx = 0;
      renderManualElementsUI();

      // Populate optional Declared Material if present in file metadata
      if (data.metadata && data.metadata.declared_material) {
        const declInput = document.getElementById('input-declared-material');
        if (declInput && !declInput.value) {
          declInput.value = data.metadata.declared_material;
        }
      }

      // Show extracted preview banner inside Drag & Drop card with ALL extracted spectra
      const previewBox = document.getElementById('file-extracted-preview');
      const previewTitle = document.getElementById('extracted-file-title');
      const badgesContainer = document.getElementById('extracted-elements-badges');
      if (previewBox && badgesContainer) {
        previewBox.classList.remove('hidden');
        if (previewTitle) {
          previewTitle.textContent = `Extracted ${data.spectra.length} Individual Spectrum${data.spectra.length > 1 ? 's' : ''} from ${file.name} (Mean/Std/Min/Max Skipped)`;
        }

        badgesContainer.innerHTML = data.spectra.map((specObj, idx) => {
          const det = detailsList[idx] || {};
          const specLabel = det.label || det.spectrum_id || `Spectrum ${idx + 1}`;
          const pageBadge = det.page ? `<span class="text-[10px] font-mono-code text-slate-400 ml-1">(Page ${det.page})</span>` : '';
          const pills = Object.entries(specObj)
            .map(([sym, wt]) => `<span class="px-1.5 py-0.5 rounded bg-slate-50 border border-slate-200 text-[10.5px] font-mono-code font-bold text-slate-800">${sym}: ${Number(wt).toFixed(2)}%</span>`)
            .join('');
          return `
            <div class="p-2 rounded-md bg-white border border-emerald-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div class="text-[11px] font-bold text-slate-800 shrink-0">
                <span class="inline-block w-4 h-4 rounded-full bg-slate-900 text-white text-[10px] font-mono-code text-center leading-4 mr-1">${idx + 1}</span>
                ${specLabel}${pageBadge}
              </div>
              <div class="flex flex-wrap gap-1">${pills}</div>
            </div>
          `;
        }).join('');
      }
      if (subStatusText) {
        subStatusText.textContent = `Extracted ${data.spectra.length} spectrum${data.spectra.length > 1 ? 's' : ''} (${data.analysed_elements.join(', ')}). Click "Start Prediction (All Spectra)" or "Analyze EDS Spectrum" to open the Multi-Spectrum Prediction & Editor page.`;
      }
    }
  } catch (err) {
    console.error('File extraction error:', err);
  }
}
window.handleFileSelected = handleFileSelected;

/* =========================================================================
   Preset Application & Form Reset
   ========================================================================= */

function applyPreset(presetId) {
  if (!presetId || !window.PRESETS_DATA) return;
  const preset = window.PRESETS_DATA.find(p => p.id === presetId);
  if (!preset) return;

  const comp = preset.composition || {};
  const selectedOrder = [];
  const values = {};

  if (comp.Fe !== undefined) {
    selectedOrder.push('Fe');
    values['Fe'] = comp.Fe;
  } else {
    selectedOrder.push('Fe');
    values['Fe'] = 'Bal.';
  }

  for (const [k, v] of Object.entries(comp)) {
    if (k === 'Fe') continue;
    if (typeof v === 'number' && v > 0) {
      selectedOrder.push(k);
      values[k] = v;
    }
  }

  uploadedFileState = null;
  currentConcentrationUnit = 'wt%';
  spectraListState[activeSpectrumIdx] = { selectedOrder, values };
  switchIngestTab('manual');
  renderManualElementsUI();
}
window.applyPreset = applyPreset;

function clearAnalyzerForm() {
  uploadedFileState = null;
  currentConcentrationUnit = 'wt%';
  elementSearchQuery = '';
  const searchInput = document.getElementById('element-search-input');
  if (searchInput) searchInput.value = '';

  spectraListState = [
    {
      selectedOrder: ['Fe', 'Ni', 'V'],
      values: { Fe: 'Bal.', Ni: 0, V: 0 },
    }
  ];
  activeSpectrumIdx = 0;
  renderManualElementsUI();

  const fileInput = document.getElementById('eds-file-input');
  if (fileInput) fileInput.value = '';
  const statusText = document.getElementById('upload-status-text');
  if (statusText) statusText.textContent = 'Drag and drop EDS file here';
  const subStatusText = document.getElementById('upload-substatus-text');
  if (subStatusText) subStatusText.textContent = 'Supports Material Analysis Reports (.pdf, .docx, .doc) and Excel files (.xlsx, .xls). Max size 10 MB.';
  const previewBox = document.getElementById('file-extracted-preview');
  if (previewBox) previewBox.classList.add('hidden');
  const declaredInput = document.getElementById('input-declared-material');
  if (declaredInput) declaredInput.value = '';
  const presetSelector = document.getElementById('preset-selector');
  if (presetSelector) presetSelector.value = '';

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

async function triggerPrediction(openDedicatedPage = true) {
  const btn = document.getElementById('btn-predict-family');
  const btnText = document.getElementById('predict-btn-text');
  const spinner = document.getElementById('predict-btn-spinner');
  const declaredMaterial = document.getElementById('input-declared-material') ? document.getElementById('input-declared-material').value.trim() : '';

  if (btn) btn.disabled = true;
  if (btnText) btnText.textContent = 'Predicting All Spectra...';
  if (spinner) spinner.classList.remove('hidden');

  const start = performance.now();

  try {
    let res;
    if (currentIngestMode === 'upload' && uploadedFileState) {
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
      // Build payload from Manual Elements state (converting at% -> wt% if needed)
      const spectraPayload = spectraListState.map(spec => {
        const wtValues = currentConcentrationUnit === 'at%'
          ? convertSpectrumUnits(spec.values, 'at%', 'wt%')
          : { ...spec.values };

        const item = {};
        spec.selectedOrder.forEach(sym => {
          if (wtValues[sym] !== undefined) {
            item[sym] = wtValues[sym];
          }
        });
        return item;
      });

      const hasData = spectraPayload.some(s => {
        const keys = Object.keys(s);
        if (keys.length === 0) return false;
        const nonFePositive = keys
          .filter(k => k !== 'Fe')
          .reduce((acc, k) => acc + (parseFloat(s[k]) || 0), 0);
        const explicitFe = s.Fe !== undefined && !String(s.Fe).toLowerCase().startsWith('bal') && parseFloat(s.Fe) > 0;
        return nonFePositive > 0 || explicitFe;
      });

      if (!hasData) {
        alert('Please select elements and enter their concentrations (or upload an EDS report file) before running analysis.');
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
    try {
      sessionStorage.setItem('DHATU_LATEST_PREDICTION', JSON.stringify(data));
    } catch (e) {
      // Ignore storage quota errors
    }

    // Open the dedicated Multi-Spectrum Prediction & Interactive Editing page
    if (openDedicatedPage !== false) {
      window.location.href = '/analyzer/results/';
      return;
    }

    renderPredictionResults(data, ((performance.now() - start) / 1000).toFixed(2));
  } catch (err) {
    console.error('Analysis execution error:', err);
    alert('Failed to communicate with the DHATU BODH analysis service.');
  } finally {
    if (btn) btn.disabled = false;
    if (btnText) btnText.textContent = 'Analyze EDS Spectrum';
    if (spinner) spinner.classList.add('hidden');
  }
}
window.triggerPrediction = triggerPrediction;

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

  // --- 2B. PROBABLE INDIRECT SOURCE (Separate Cleaning Area Rule Engine) ---
  renderIndirectSourceCard(data);

  // --- 3. COMPOSITION BREAKDOWN (MEASURED VS EXPECTED BANDS) ---
  renderCompositionBreakdown(data);

  // --- 4. RATIO GATE ANALYSIS ---
  renderRatioGates(data);

  // --- 5. ALTERNATIVE CANDIDATES TABLE ---
  renderCandidatesTable(data);

  // --- 6. WARNINGS & CONFLICTS ---
  renderWarningsAndConflicts(data);
}

function renderIndirectSourceCard(data) {
  const card = document.getElementById('probable-indirect-source-card');
  if (!card) return;

  const ind = data.indirectSourcePrediction || null;
  if (!ind) {
    card.classList.add('hidden');
    return;
  }

  card.classList.remove('hidden');
  const famBadge = document.getElementById('indirect-source-family-badge');
  const decBadge = document.getElementById('indirect-source-decision-badge');
  const partNameEl = document.getElementById('indirect-source-part-name');
  const locEl = document.getElementById('indirect-source-location');
  const ratEl = document.getElementById('indirect-source-rationale');
  const pctEl = document.getElementById('indirect-source-compat-pct');
  const tolEl = document.getElementById('indirect-source-tol-summary');
  const elBox = document.getElementById('indirect-source-elements-box');
  const altBox = document.getElementById('indirect-source-alternatives-box');

  const indFamily = ind.indirectFamily || ind.predictedMaterialFamily || 'Unknown / Inconclusive';
  const indDecision = ind.decision || 'unknown';
  const topSource = ind.topIndirectSource || null;
  const isUnknown = indDecision === 'unknown' || !topSource;

  if (famBadge) {
    famBadge.textContent = `Stage 1 Indirect Family: ${indFamily}`;
  }

  if (decBadge) {
    if (indDecision === 'identified') {
      decBadge.className = 'px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-200';
      decBadge.textContent = 'IDENTIFIED';
    } else if (indDecision === 'ambiguous' || indDecision === 'multiple_plausible') {
      decBadge.className = 'px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-100 text-amber-800 border border-amber-200';
      decBadge.textContent = 'MULTIPLE PLAUSIBLE';
    } else {
      decBadge.className = 'px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-700 border border-slate-300';
      decBadge.textContent = 'UNKNOWN / INCONCLUSIVE';
    }
  }

  if (isUnknown) {
    if (partNameEl) partNameEl.textContent = 'Unknown / Inconclusive';
    if (locEl) locEl.textContent = 'No compatible Cleaning Area indirect source matched';
    if (ratEl) ratEl.textContent = ind.stage1Reason || ind.decisionRationale || 'Insufficient elemental compatibility with Cleaning Area reference parts.';
    if (pctEl) pctEl.textContent = '—';
    if (tolEl) tolEl.textContent = 'No match';
    if (elBox) elBox.innerHTML = '';
    if (altBox) altBox.innerHTML = '';
    return;
  }

  if (partNameEl) partNameEl.textContent = topSource.partName || 'Unknown / Inconclusive';
  if (locEl) locEl.textContent = `Location: ${topSource.location || 'Cleaning Area'} • Material Class: ${topSource.material || indFamily}`;
  if (ratEl) ratEl.textContent = topSource.notes || ind.stage1Reason || '';
  if (pctEl) pctEl.textContent = `${topSource.compatibilityPct || 0}%`;
  if (tolEl) {
    const wCount = (topSource.withinToleranceElements || []).length;
    const oCount = (topSource.outsideToleranceElements || []).length;
    const mCount = (topSource.missingElements || []).length;
    tolEl.textContent = `${wCount} in-tol / ${oCount} out / ${mCount} missing`;
  }

  if (elBox) {
    const evals = topSource.elementChecks || [];
    elBox.innerHTML = evals.map(ev => {
      const measStr = ev.measuredValue !== null && ev.measuredValue !== undefined ? `${Number(ev.measuredValue).toFixed(2)}%` : 'N/A';
      const rangeStr = `[${Number(ev.minValue).toFixed(2)}–${Number(ev.maxValue).toFixed(2)}%]`;
      let cls = 'bg-emerald-50 text-emerald-800 border-emerald-200';
      if (ev.status !== 'within_tolerance') {
        cls = ev.status === 'missing'
          ? 'bg-rose-50 text-rose-800 border-rose-200'
          : 'bg-amber-50 text-amber-800 border-amber-200';
      }
      return `<span class="px-2 py-0.5 rounded border text-[10.5px] font-mono-code font-semibold ${cls}">${ev.element}: ${measStr} ${rangeStr}</span>`;
    }).join('');
  }

  if (altBox) {
    const alts = (ind.candidates || []).slice(1, 5);
    if (alts.length > 0) {
      altBox.innerHTML = `<span class="font-bold text-slate-700 mr-1.5">Plausible Indirect Alternatives:</span>` +
        alts.map(a => `<span class="inline-block px-2 py-0.5 mr-1.5 mb-1 rounded bg-slate-100 border border-slate-200 font-semibold text-slate-800">${a.partName} <span class="font-mono-code text-indigo-700">(${a.compatibilityPct}%)</span></span>`).join('');
    } else {
      altBox.innerHTML = `<span class="text-slate-400">No other indirect parts in ${indFamily} exceeded compatibility threshold.</span>`;
    }
  }
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
