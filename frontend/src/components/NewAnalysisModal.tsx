import React, { useState, useEffect, useRef } from 'react';

interface NewAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  isDarkMode: boolean;
  onStartSession: (info: { particleId: string; spectrometer: string; description: string }) => void;
}

export const NewAnalysisModal: React.FC<NewAnalysisModalProps> = ({
  isOpen,
  onClose,
  isDarkMode,
  onStartSession,
}) => {
  const [selectedSpectrometer, setSelectedSpectrometer] = useState('Oxford Instruments Aztec (20 kV)');
  const [particleId, setParticleId] = useState(`P-${Math.floor(10000 + Math.random() * 90000)}`);
  const [sampleDescription, setSampleDescription] = useState('');
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const el = panelRef.current?.querySelector<HTMLElement>(
      '[tabindex]:not([tabindex="-1"]), button, input, select, textarea, a[href]'
    );
    el?.focus();
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onStartSession({
      particleId,
      spectrometer: selectedSpectrometer,
      description: sampleDescription || 'Debris microanalysis',
    });
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
                biotech
              </span>
              <h3 className="font-display text-[20px] font-bold" style={{ color: 'var(--color-text-primary)' }}>
                Initialize New Particle Scan
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

          <form onSubmit={handleSubmit} className="space-y-4 text-[13px]">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label
                  className="block text-[11px] font-bold uppercase tracking-wider mb-1 opacity-70"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  Sample / Particle ID
                </label>
                <input
                  type="text"
                  required
                  value={particleId}
                  onChange={(e) => setParticleId(e.target.value)}
                  className="w-full p-2 font-mono-code focus:outline-none"
                  style={{
                    background: 'var(--color-bg-base)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                    color: 'var(--color-text-primary)',
                  }}
                />
              </div>
              <div>
                <label
                  className="block text-[11px] font-bold uppercase tracking-wider mb-1 opacity-70"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  Spectrometer Source
                </label>
                <select
                  value={selectedSpectrometer}
                  onChange={(e) => setSelectedSpectrometer(e.target.value)}
                  className="w-full p-2 focus:outline-none"
                  style={{
                    background: 'var(--color-bg-base)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                    color: 'var(--color-text-primary)',
                  }}
                >
                  <option value="Oxford Instruments Aztec (20 kV)">Oxford Instruments Aztec (20 kV)</option>
                  <option value="Thermo Fisher Phenom XL">Thermo Fisher Phenom XL</option>
                  <option value="Bruker ESPRIT EDS">Bruker ESPRIT EDS</option>
                  <option value="JEOL JSM-IT800">JEOL JSM-IT800</option>
                  <option value="Zeiss EVO 15 MA">Zeiss EVO 15 MA</option>
                </select>
              </div>
            </div>

            <div>
              <label
                className="block text-[11px] font-bold uppercase tracking-wider mb-1 opacity-70"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                Sample Context / Sampling Location
              </label>
              <input
                type="text"
                placeholder="e.g. Filter basket wear particle, scavenge oil return..."
                value={sampleDescription}
                onChange={(e) => setSampleDescription(e.target.value)}
                className="w-full p-2 focus:outline-none"
                style={{
                  background: 'var(--color-bg-base)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--color-text-primary)',
                }}
              />
            </div>

            <div
              className="p-3 text-[12px] flex gap-2.5 items-center"
              style={{
                background: 'var(--color-accent-subtle)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              <span
                className="material-symbols-outlined text-[20px]"
                style={{ color: 'var(--color-pass)' }}
              >
                verified
              </span>
              <span style={{ color: 'var(--color-text-secondary)' }}>
                Clean scan session will be initialized ready for manual elemental entry or EDS report upload.
              </span>
            </div>

            <div
              className="mt-6 flex justify-end gap-2 pt-3"
              style={{ borderTop: '1px solid var(--color-border)' }}
            >
              <button
                type="button"
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
                type="submit"
                className="press-target px-5 py-2 text-[13px] font-semibold"
                style={{
                  background: 'var(--color-accent)',
                  color: 'var(--color-accent-on)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                Initialize Session
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
