import React, { useState, useEffect, useRef } from 'react';
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
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const el = panelRef.current?.querySelector<HTMLElement>(
      '[tabindex]:not([tabindex="-1"]), button, input, select, textarea, a[href]'
    );
    el?.focus();
  }, [isOpen]);

  if (!isOpen) return null;

  const handleDownload = () => {
    const code = activeFamily?.code || 'LAB';
    if (exportFormat === 'json') {
      const dataStr = JSON.stringify(
        {
          system: 'Dhatu Bodh Spectral Lab v2.4',
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
    <div className="fixed inset-0 z-[100] flex items-center justify-center modal-overlay p-4">
      <div className="anim-spring-in w-full max-w-lg">
        <div
          ref={panelRef}
          className="w-full p-6"
          style={{
            background: 'var(--color-bg-card)',
            border: '1px solid var(--color-border)',
            boxShadow: 'var(--shadow-modal)',
            borderRadius: 'var(--radius-xl)',
            color: 'var(--color-text-primary)',
          }}
        >
          {/* Header */}
          <div
            className="flex justify-between items-center mb-4 pb-3"
            style={{ borderBottom: '1px solid var(--color-border)' }}
          >
            <div className="flex items-center gap-2">
              <span
                className="material-symbols-outlined text-[22px]"
                style={{ color: 'var(--color-accent)' }}
              >
                download
              </span>
              <h3 className="font-display text-[20px] font-bold" style={{ color: 'var(--color-text-primary)' }}>
                Export Laboratory Data
              </h3>
            </div>
            <button
              onClick={onClose}
              className="press-target p-1 rounded"
              style={{ color: 'var(--color-text-tertiary)' }}
            >
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>

          <div className="space-y-4 text-[13px]">
            <div>
              <label
                className="block text-[11px] font-bold uppercase tracking-wider mb-2 opacity-70"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                Select Export Format
              </label>
              <div className="grid grid-cols-3 gap-2.5">
                {[
                  { id: 'pdf', label: 'PDF Report', icon: 'picture_as_pdf' },
                  { id: 'csv', label: 'CSV Dataset', icon: 'table_view' },
                  { id: 'json', label: 'Raw JSON', icon: 'data_object' },
                ].map((fmt) => {
                  const isSelected = exportFormat === fmt.id;
                  return (
                    <button
                      key={fmt.id}
                      type="button"
                      onClick={() => setExportFormat(fmt.id as any)}
                      className="press-target p-3 text-center border transition-all"
                      style={{
                        borderRadius: 'var(--radius-md)',
                        background: isSelected ? 'var(--color-accent-subtle)' : 'var(--color-bg-elevated)',
                        borderColor: isSelected ? 'var(--color-accent)' : 'var(--color-border)',
                        color: isSelected ? 'var(--color-accent)' : 'var(--color-text-primary)',
                        fontWeight: isSelected ? 600 : 400,
                      }}
                    >
                      <span className="material-symbols-outlined text-[24px] block mx-auto mb-1">
                        {fmt.icon}
                      </span>
                      {fmt.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div
              className="space-y-2 pt-3"
              style={{ borderTop: '1px solid var(--color-border)' }}
            >
              <label className="flex items-center gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeAuditLog}
                  onChange={(e) => setIncludeAuditLog(e.target.checked)}
                  style={{ accentColor: 'var(--color-accent)' }}
                />
                <span style={{ color: 'var(--color-text-secondary)' }}>
                  Include full audit trail trace and calibration metadata
                </span>
              </label>
              <label className="flex items-center gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeSpectraRaw}
                  onChange={(e) => setIncludeSpectraRaw(e.target.checked)}
                  style={{ accentColor: 'var(--color-accent)' }}
                />
                <span style={{ color: 'var(--color-text-secondary)' }}>
                  Include stoichiometric ratio gate definitions ({activeFamily?.ratioGates?.length ?? 0} gates)
                </span>
              </label>
            </div>
          </div>

          <div
            className="mt-6 flex justify-end gap-2 pt-3"
            style={{ borderTop: '1px solid var(--color-border)' }}
          >
            <button
              onClick={onClose}
              className="press-target px-4 py-2 text-[13px] font-semibold"
              style={{
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--color-text-secondary)',
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleDownload}
              className="press-target px-5 py-2 text-[13px] font-semibold"
              style={{
                background: 'var(--color-accent)',
                color: 'var(--color-accent-on)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              Generate & Download
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
