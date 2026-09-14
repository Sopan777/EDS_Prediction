import React from 'react';
import { CandidateComponent } from '../types';

interface ComponentModalProps {
  component: CandidateComponent | null;
  onClose: () => void;
  isDarkMode: boolean;
}

export const ComponentModal: React.FC<ComponentModalProps> = ({
  component,
  onClose,
  isDarkMode,
}) => {
  if (!component) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div
        className={`w-full max-w-lg rounded-xl border shadow-2xl p-6 transition-colors ${
          isDarkMode ? 'bg-[#0c1512] border-[#3a4a44] text-[#dbe5df]' : 'bg-white border-[#c0c8c2] text-[#191c1e]'
        }`}
      >
        {/* Header */}
        <div className="flex justify-between items-start mb-4 pb-3 border-b border-inherit">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={`px-2 py-0.5 rounded text-[11px] font-mono-code font-bold ${
                isDarkMode ? 'bg-[#151d1a] text-[#00ffcc]' : 'bg-[#f2f4f6] text-[#134231]'
              }`}>
                {component.partNumber}
              </span>
              <span className="text-[12px] opacity-60">• {component.category}</span>
            </div>
            <h3 className="font-display text-[22px] font-bold">{component.name}</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded text-gray-400 hover:text-white">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {/* Content details */}
        <div className="space-y-4 text-[13px]">
          <div className="grid grid-cols-2 gap-3">
            <div className={`p-3 rounded-lg border ${isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'}`}>
              <span className="text-[11px] font-bold uppercase tracking-wider block mb-1 opacity-60">
                Nominal Metallurgy
              </span>
              <span className="font-semibold">{component.nominalAlloy}</span>
            </div>
            <div className={`p-3 rounded-lg border ${isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'}`}>
              <span className="text-[11px] font-bold uppercase tracking-wider block mb-1 opacity-60">
                Cross-Match Confidence
              </span>
              <span className="font-mono-code font-bold text-emerald-500 text-[15px]">
                {component.confidence}%
              </span>
            </div>
          </div>

          <div className={`p-3 rounded-lg border ${isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'}`}>
            <h4 className="text-[11px] font-bold uppercase tracking-wider mb-1.5 opacity-60">
              Laboratory Engineering Notes
            </h4>
            <p className="leading-relaxed">
              {component.notes ||
                'High-friction contact face subject to cyclical fatigue wear. Particulate debris routinely correlates with standard austenitic stainless steel signatures.'}
            </p>
          </div>

          <div className="flex items-center justify-between py-2 border-t border-inherit text-[12px]">
            <span className="opacity-70">ASTM Standard Ref: E1508 / E2142</span>
            <span className="font-mono-code">Spectral Library v2.4 Verified</span>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            className={`px-4 py-2 rounded-lg text-[13px] font-semibold border ${
              isDarkMode ? 'border-[#3a4a44] hover:bg-[#151d1a]' : 'border-[#c0c8c2] hover:bg-[#f2f4f6]'
            }`}
          >
            Close
          </button>
          <button
            onClick={() => {
              alert(`Exporting CAD specs and metallurgical certificate for ${component.name} (${component.partNumber})...`);
              onClose();
            }}
            className="px-4 py-2 rounded-lg text-[13px] font-semibold bg-emerald-600 text-white hover:bg-emerald-700"
          >
            Export Spec Sheet
          </button>
        </div>
      </div>
    </div>
  );
};
