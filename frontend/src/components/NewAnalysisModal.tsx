import React, { useState } from 'react';

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
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div
        className={`w-full max-w-lg rounded-xl border shadow-2xl p-6 transition-colors ${
          isDarkMode ? 'bg-[#0c1512] border-[#3a4a44] text-[#dbe5df]' : 'bg-white border-[#c0c8c2] text-[#191c1e]'
        }`}
      >
        <div className="flex justify-between items-center mb-4 pb-3 border-b border-inherit">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[22px] text-emerald-500">
              biotech
            </span>
            <h3 className="font-display text-[20px] font-bold">Initialize New Particle Scan</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded text-gray-400 hover:text-white">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-[13px]">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wider mb-1 opacity-70">
                Sample / Particle ID
              </label>
              <input
                type="text"
                required
                value={particleId}
                onChange={(e) => setParticleId(e.target.value)}
                className={`w-full border rounded p-2 font-mono-code ${
                  isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'
                }`}
              />
            </div>
            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wider mb-1 opacity-70">
                Spectrometer Source
              </label>
              <select
                value={selectedSpectrometer}
                onChange={(e) => setSelectedSpectrometer(e.target.value)}
                className={`w-full border rounded p-2 ${
                  isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'
                }`}
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
            <label className="block text-[11px] font-bold uppercase tracking-wider mb-1 opacity-70">
              Sample Context / Sampling Location
            </label>
            <input
              type="text"
              placeholder="e.g. Filter basket wear particle, scavenge oil return..."
              value={sampleDescription}
              onChange={(e) => setSampleDescription(e.target.value)}
              className={`w-full border rounded p-2 ${
                isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'
              }`}
            />
          </div>

          <div
            className={`p-3 rounded-lg border text-[12px] flex gap-2.5 items-center ${
              isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'
            }`}
          >
            <span className="material-symbols-outlined text-[20px] text-emerald-500">
              verified
            </span>
            <span>
              Clean scan session will be initialized ready for manual elemental entry or EDS report upload.
            </span>
          </div>

          <div className="mt-6 flex justify-end gap-2 pt-3 border-t border-inherit">
            <button
              type="button"
              onClick={onClose}
              className={`px-4 py-2 rounded-lg text-[13px] font-semibold border ${
                isDarkMode ? 'border-[#3a4a44] hover:bg-[#151d1a]' : 'border-[#c0c8c2] hover:bg-[#f2f4f6]'
              }`}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={`px-5 py-2 rounded-lg text-[13px] font-semibold shadow ${
                isDarkMode ? 'bg-[#00ffcc] text-[#00382b] hover:bg-[#24ffcd]' : 'bg-[#134231] text-white hover:bg-[#2d5a47]'
              }`}
            >
              Initialize Session
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
