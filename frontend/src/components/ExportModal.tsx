import React, { useState } from 'react';
import { MaterialFamily } from '../types';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  isDarkMode: boolean;
  activeFamily: MaterialFamily | null;
}

export const ExportModal: React.FC<ExportModalProps> = ({
  isOpen,
  onClose,
  isDarkMode,
  activeFamily,
}) => {
  const [exportFormat, setExportFormat] = useState<'pdf' | 'csv' | 'json'>('pdf');
  const [includeAuditLog, setIncludeAuditLog] = useState(true);
  const [includeSpectraRaw, setIncludeSpectraRaw] = useState(true);

  if (!isOpen) return null;

  const handleDownload = () => {
    const code = activeFamily?.code || 'LAB';
    if (exportFormat === 'json') {
      const dataStr = JSON.stringify(
        {
          system: 'Spectral Lab MaterialID v2.4',
          exportTimestamp: new Date().toISOString(),
          identifiedFamily: activeFamily || null,
          standards: ['ASTM E1508', 'ISO 22309'],
        },
        null,
        2
      );
      const blob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `spectral_report_${code}_${Date.now()}.json`;
      a.click();
    } else if (exportFormat === 'csv') {
      const bands = activeFamily?.elementBands || [];
      const csvData = [
        ['Element', 'Role', 'Min wt%', 'Max wt%', 'Spectra Support'],
        ...bands.map((b) => [
          b.element,
          b.role,
          b.rangeMin,
          b.rangeMax,
          b.spectraSupport,
        ]),
      ]
        .map((r) => r.join(','))
        .join('\n');
      const blob = new Blob([csvData], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `material_bands_${code}_${Date.now()}.csv`;
      a.click();
    } else {
      window.print();
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div
        className={`w-full max-w-lg rounded-xl border shadow-2xl p-6 transition-colors ${
          isDarkMode ? 'bg-[#0c1512] border-[#3a4a44] text-[#dbe5df]' : 'bg-white border-[#c0c8c2] text-[#191c1e]'
        }`}
      >
        <div className="flex justify-between items-center mb-4 pb-3 border-b border-inherit">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[22px] text-emerald-500">
              download
            </span>
            <h3 className="font-display text-[20px] font-bold">Export Laboratory Data</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded text-gray-400 hover:text-white">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <div className="space-y-4 text-[13px]">
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider mb-2 opacity-70">
              Select Export Format
            </label>
            <div className="grid grid-cols-3 gap-2.5">
              <button
                type="button"
                onClick={() => setExportFormat('pdf')}
                className={`p-3 rounded-lg border text-center transition-all ${
                  exportFormat === 'pdf'
                    ? isDarkMode
                      ? 'bg-[#151d1a] border-[#00ffcc] text-[#00ffcc]'
                      : 'bg-[#f2f4f6] border-[#134231] text-[#134231] font-bold'
                    : 'border-inherit opacity-70 hover:opacity-100'
                }`}
              >
                <span className="material-symbols-outlined text-[24px] block mx-auto mb-1">
                  picture_as_pdf
                </span>
                PDF Report
              </button>

              <button
                type="button"
                onClick={() => setExportFormat('csv')}
                className={`p-3 rounded-lg border text-center transition-all ${
                  exportFormat === 'csv'
                    ? isDarkMode
                      ? 'bg-[#151d1a] border-[#00ffcc] text-[#00ffcc]'
                      : 'bg-[#f2f4f6] border-[#134231] text-[#134231] font-bold'
                    : 'border-inherit opacity-70 hover:opacity-100'
                }`}
              >
                <span className="material-symbols-outlined text-[24px] block mx-auto mb-1">
                  table_view
                </span>
                CSV Dataset
              </button>

              <button
                type="button"
                onClick={() => setExportFormat('json')}
                className={`p-3 rounded-lg border text-center transition-all ${
                  exportFormat === 'json'
                    ? isDarkMode
                      ? 'bg-[#151d1a] border-[#00ffcc] text-[#00ffcc]'
                      : 'bg-[#f2f4f6] border-[#134231] text-[#134231] font-bold'
                    : 'border-inherit opacity-70 hover:opacity-100'
                }`}
              >
                <span className="material-symbols-outlined text-[24px] block mx-auto mb-1">
                  data_object
                </span>
                Raw JSON
              </button>
            </div>
          </div>

          <div className="space-y-2 pt-2 border-t border-inherit">
            <label className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={includeAuditLog}
                onChange={(e) => setIncludeAuditLog(e.target.checked)}
                className="rounded text-emerald-600 focus:ring-emerald-500"
              />
              <span>Include full audit trail trace and calibration metadata</span>
            </label>
            <label className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={includeSpectraRaw}
                onChange={(e) => setIncludeSpectraRaw(e.target.checked)}
                className="rounded text-emerald-600 focus:ring-emerald-500"
              />
              <span>Include stoichiometric ratio gate definitions ({activeFamily.ratioGates.length} gates)</span>
            </label>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2 pt-3 border-t border-inherit">
          <button
            onClick={onClose}
            className={`px-4 py-2 rounded-lg text-[13px] font-semibold border ${
              isDarkMode ? 'border-[#3a4a44] hover:bg-[#151d1a]' : 'border-[#c0c8c2] hover:bg-[#f2f4f6]'
            }`}
          >
            Cancel
          </button>
          <button
            onClick={handleDownload}
            className="px-5 py-2 rounded-lg text-[13px] font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm"
          >
            Generate & Download
          </button>
        </div>
      </div>
    </div>
  );
};
