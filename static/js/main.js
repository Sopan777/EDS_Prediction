/**
 * static/js/main.js
 * =================
 * Global application utilities: theme switching, modals, CSRF handling.
 */

// Theme Management
function toggleTheme() {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('spectral_theme', isDark ? 'dark' : 'light');
  updateThemeIcon(isDark);
}

function updateThemeIcon(isDark) {
  const icon = document.getElementById('theme-icon');
  if (icon) {
    icon.textContent = isDark ? 'light_mode' : 'dark_mode';
  }
}

// Initial theme icon sync
document.addEventListener('DOMContentLoaded', () => {
  const isDark = document.documentElement.classList.contains('dark');
  updateThemeIcon(isDark);
});

// CSRF Token Helper
function getCSRFToken() {
  const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
  if (csrfInput) return csrfInput.value;

  const cookieValue = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
  return cookieValue || '';
}

// Component Spec Modal
let currentSelectedComponent = null;

function openComponentModal(comp) {
  currentSelectedComponent = comp;
  document.getElementById('modal-comp-name').textContent = comp.name || 'Component';
  document.getElementById('modal-comp-partno').textContent = comp.partNumber || 'BOSCH-EDS-REF';
  document.getElementById('modal-comp-category').textContent = `• ${comp.category || 'Precision Component'}`;
  document.getElementById('modal-comp-alloy').textContent = comp.nominalAlloy || 'Standard Alloy';
  document.getElementById('modal-comp-conf').textContent = `${comp.confidence || 95}%`;
  document.getElementById('modal-comp-notes').textContent = comp.notes || 'Observed reference component for this material family.';

  document.getElementById('component-modal').classList.remove('hidden');
}

function closeComponentModal() {
  document.getElementById('component-modal').classList.add('hidden');
}

// Export Modal
let currentExportFormat = 'pdf';

function openExportModal() {
  document.getElementById('export-modal').classList.remove('hidden');
}

function closeExportModal() {
  document.getElementById('export-modal').classList.add('hidden');
}

function setExportFormat(fmt) {
  currentExportFormat = fmt;
  ['pdf', 'csv', 'json'].forEach(f => {
    const btn = document.getElementById(`export-fmt-${f}`);
    if (!btn) return;
    if (f === fmt) {
      btn.className = 'p-3 rounded-lg border text-center transition-all bg-[#f2f4f6] border-[#134231] text-[#134231] font-bold dark:bg-[#151d1a] dark:border-[#00ffcc] dark:text-[#00ffcc]';
    } else {
      btn.className = 'p-3 rounded-lg border text-center transition-all border-gray-300 dark:border-[#3a4a44] hover:border-emerald-500';
    }
  });
}

function executeExportDownload() {
  const code = (window.ACTIVE_FAMILY && window.ACTIVE_FAMILY.code) || 'LAB';
  if (currentExportFormat === 'json') {
    const dataStr = JSON.stringify({
      system: 'Spectral Lab MaterialID v2.4 (Django Edition)',
      exportTimestamp: new Date().toISOString(),
      standards: ['ASTM E1508', 'ISO 22309'],
      activeFamily: window.ACTIVE_FAMILY || null,
    }, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `spectral_report_${code}_${Date.now()}.json`;
    a.click();
  } else if (currentExportFormat === 'csv') {
    const bands = (window.ACTIVE_FAMILY && window.ACTIVE_FAMILY.elementBands) || [];
    const csvData = [
      ['Element', 'Role', 'Min wt%', 'Max wt%', 'Spectra Support'],
      ...bands.map(b => [b.element, b.role, b.rangeMin, b.rangeMax, b.spectraSupport]),
    ].map(r => r.join(',')).join('\n');
    const blob = new Blob([csvData], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `material_bands_${code}_${Date.now()}.csv`;
    a.click();
  } else {
    window.print();
  }
  closeExportModal();
}

// New Analysis Modal
function openNewAnalysisModal() {
  const randNum = Math.floor(10000 + Math.random() * 90000);
  const partInput = document.getElementById('modal-particle-id');
  if (partInput) partInput.value = `P-${randNum}`;
  document.getElementById('new-analysis-modal').classList.remove('hidden');
}

function closeNewAnalysisModal() {
  document.getElementById('new-analysis-modal').classList.add('hidden');
}

function handleStartNewSession(event) {
  event.preventDefault();
  closeNewAnalysisModal();
  if (window.location.pathname !== '/' && window.location.pathname !== '/analyzer/') {
    window.location.href = '/';
  } else if (window.clearAnalyzerForm) {
    window.clearAnalyzerForm();
  }
}

// Global search bar
document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('global-search-input');
  if (searchInput) {
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const query = searchInput.value.trim();
        if (!query) return;
        // If on knowledge base, trigger filter
        const filterInput = document.getElementById('filter-families-input');
        if (filterInput) {
          filterInput.value = query;
          filterInput.dispatchEvent(new Event('input'));
        } else {
          window.location.href = `/knowledge/?family=${encodeURIComponent(query)}`;
        }
      }
    });
  }

  // Close modals on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeComponentModal();
      closeExportModal();
      closeNewAnalysisModal();
    }
  });
});
