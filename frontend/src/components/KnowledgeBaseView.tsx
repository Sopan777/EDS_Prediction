import React, { useState } from 'react';
import { MaterialFamily, CandidateComponent } from '../types';

interface KnowledgeBaseViewProps {
  isDarkMode: boolean;
  activeFamily?: MaterialFamily;
  onSelectFamily: (f: MaterialFamily) => void;
  onOpenGateEditor: () => void;
  onSelectComponent: (comp: CandidateComponent) => void;
  families: MaterialFamily[];
}

export const KnowledgeBaseView: React.FC<KnowledgeBaseViewProps> = ({
  isDarkMode,
  activeFamily,
  onSelectFamily,
  onOpenGateEditor,
  onSelectComponent,
  families,
}) => {
  const [filterQuery, setFilterQuery] = useState('');
  const [showAllComponents, setShowAllComponents] = useState(false);

  if (!activeFamily || families.length === 0) {
    return (
      <div id="knowledge-base-screen" className="flex flex-col items-center justify-center h-full p-8 text-center">
        <div
          className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-4 ${
            isDarkMode ? 'bg-[#151d1a] text-[#83958d]' : 'bg-[#f2f4f6] text-[#717974]'
          }`}
        >
          <span className="material-symbols-outlined text-[36px]">menu_book</span>
        </div>
        <h3 className={`text-[18px] font-bold mb-2 ${isDarkMode ? 'text-white' : 'text-[#191c1e]'}`}>
          No Material Families in Knowledge Base
        </h3>
        <p className={`text-[13px] max-w-md ${isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'}`}>
          The metallurgical knowledge base is currently empty. Establish standard ASTM/ISO alloy families to configure elemental gates.
        </p>
      </div>
    );
  }

  const filteredFamilies = families.filter(
    (f) =>
      f.code.toLowerCase().includes(filterQuery.toLowerCase()) ||
      f.name.toLowerCase().includes(filterQuery.toLowerCase()) ||
      f.description.toLowerCase().includes(filterQuery.toLowerCase())
  );

  return (
    <div id="knowledge-base-screen" className="flex gap-6 h-full overflow-hidden">
      {/* Left Column: Material Families List (1/3 width) */}
      <section className="w-1/3 flex flex-col gap-4">
        <div
          className={`rounded-xl border shadow-sm p-4 flex flex-col h-full overflow-hidden transition-colors ${
            isDarkMode
              ? 'bg-[#07100d] border-[#3a4a44]'
              : 'bg-white border-[#c0c8c2]'
          }`}
        >
          {/* Header */}
          <div className="flex justify-between items-center mb-3">
            <h3
              className={`font-semibold text-[16px] tracking-tight ${
                isDarkMode ? 'text-white' : 'text-[#134231]'
              }`}
            >
              Material Families
            </h3>
            <span className={`text-[11px] font-mono-code ${isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'}`}>
              {families.length} {families.length === 1 ? 'family' : 'families'}
            </span>
          </div>

          {/* Filter input */}
          <div className="mb-3">
            <input
              id="filter-families-input"
              type="text"
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              placeholder="Filter families (e.g., F4, Austenitic)..."
              className={`w-full px-3 py-2 text-[13px] rounded-md border focus:outline-none transition-colors ${
                isDarkMode
                  ? 'bg-[#151d1a] border-[#3a4a44] text-[#dbe5df] focus:border-[#00ffcc]'
                  : 'bg-[#f2f4f6] border-[#c0c8c2] text-[#191c1e] focus:border-[#134231]'
              }`}
            />
          </div>

          {/* Families list */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {filteredFamilies.length === 0 ? (
              <div className="py-8 text-center text-[12px] opacity-60">
                No matching material families
              </div>
            ) : (
              filteredFamilies.map((fam) => {
                const isSelected = fam.id === activeFamily.id;
                return (
                  <div
                    key={fam.id}
                    onClick={() => onSelectFamily(fam)}
                    className={`p-3 rounded-lg border cursor-pointer transition-all ${
                      isSelected
                        ? isDarkMode
                          ? 'bg-[#19211e] border-[#00ffcc] border-l-4 border-l-[#00ffcc] shadow-sm'
                          : 'bg-white border-[#006b5b] border-l-4 border-l-[#006b5b] shadow-sm'
                        : isDarkMode
                        ? 'bg-[#0c1512] border-[#3a4a44] hover:border-[#83958d]'
                        : 'bg-white border-[#c0c8c2] hover:border-[#717974]'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span
                        className={`font-mono-code text-[13px] font-bold ${
                          isSelected
                            ? isDarkMode
                              ? 'text-[#00ffcc]'
                              : 'text-[#006b5b]'
                            : isDarkMode
                            ? 'text-[#b9cbc2]'
                            : 'text-[#414944]'
                        }`}
                      >
                        {fam.code}
                      </span>

                      {fam.status === 'FIRM' ? (
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                            isDarkMode
                              ? 'bg-[#00ffcc] text-[#00382b]'
                              : 'bg-[#bcedd4] text-[#002115]'
                          }`}
                        >
                          FIRM
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border border-dashed border-[#83958d] text-[#83958d]">
                          PROV
                        </span>
                      )}
                    </div>
                    <h4
                      className={`text-[14px] font-semibold ${
                        isDarkMode ? 'text-white' : 'text-[#191c1e]'
                      }`}
                    >
                      {fam.name}
                    </h4>
                    <p
                      className={`text-[12px] mt-0.5 ${
                        isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                      }`}
                    >
                      {fam.description}
                    </p>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </section>

      {/* Right Column: Details View (2/3 width) */}
      <section className="w-2/3 flex flex-col gap-4 overflow-y-auto pr-1 pb-6">
        {/* Header Card */}
        <div
          className={`rounded-xl border shadow-sm p-6 transition-colors ${
            isDarkMode
              ? 'bg-[#07100d] border-[#3a4a44]'
              : 'bg-white border-[#c0c8c2]'
          }`}
        >
          <div className="flex justify-between items-start">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span
                  className={`font-mono-code text-[14px] font-bold px-2 py-0.5 rounded ${
                    isDarkMode
                      ? 'bg-[#151d1a] text-[#00ffcc]'
                      : 'bg-[#f2f4f6] text-[#006b5b]'
                  }`}
                >
                  {activeFamily.code}
                </span>

                <span
                  className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider flex items-center gap-1 ${
                    isDarkMode
                      ? 'bg-[#00ffcc] text-[#00382b]'
                      : 'bg-[#134231] text-white'
                  }`}
                >
                  <span className="material-symbols-outlined text-[13px]">verified</span>
                  {activeFamily.status} FAMILY
                </span>
              </div>

              <h2
                className={`font-display text-[28px] md:text-[32px] font-bold tracking-tight mb-1 ${
                  isDarkMode ? 'text-white' : 'text-[#134231]'
                }`}
              >
                {activeFamily.name}
              </h2>
              <p
                className={`text-[13px] flex items-center gap-1.5 ${
                  isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                }`}
              >
                <span className="material-symbols-outlined text-[15px]">info</span>
                Grade hint: {activeFamily.gradeHint}
              </p>
            </div>

            <button
              id="btn-edit-profile"
              onClick={onOpenGateEditor}
              className={`px-4 py-2 border rounded-lg text-[13px] font-semibold transition-all shadow-sm ${
                isDarkMode
                  ? 'border-[#00ffcc] text-[#00ffcc] hover:bg-[#00ffcc]/10'
                  : 'border-[#006b5b] text-[#006b5b] hover:bg-[#f2f4f6]'
              }`}
            >
              Edit Profile
            </button>
          </div>
        </div>

        {/* Elemental Composition Bands Table */}
        <div
          className={`rounded-xl border shadow-sm overflow-hidden flex flex-col transition-colors ${
            isDarkMode
              ? 'bg-[#07100d] border-[#3a4a44]'
              : 'bg-white border-[#c0c8c2]'
          }`}
        >
          <div
            className={`p-4 border-b flex justify-between items-center ${
              isDarkMode ? 'border-[#3a4a44]' : 'border-[#c0c8c2]'
            }`}
          >
            <div className="flex items-center gap-2">
              <span
                className={`material-symbols-outlined text-[20px] ${
                  isDarkMode ? 'text-[#00ffcc]' : 'text-[#006b5b]'
                }`}
              >
                layers
              </span>
              <h3
                className={`font-semibold text-[15px] ${
                  isDarkMode ? 'text-white' : 'text-[#134231]'
                }`}
              >
                Baseline Elemental Composition
              </h3>
            </div>
            <span
              className={`text-[11px] font-mono-code ${
                isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'
              }`}
            >
              ASTM E1508 Validated
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-[13px]">
              <thead>
                <tr
                  className={`border-b text-[11px] font-bold uppercase tracking-wider ${
                    isDarkMode
                      ? 'bg-[#151d1a] border-[#3a4a44] text-[#83958d]'
                      : 'bg-[#f7f9fb] border-[#c0c8c2] text-[#414944]'
                  }`}
                >
                  <th className="p-3">Element</th>
                  <th className="p-3">Expected Range (wt%)</th>
                  <th className="p-3">Spectra Support</th>
                  <th className="p-3">Confidence Range</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-inherit">
                {activeFamily.baselineElements.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-[12px] opacity-60">
                      No baseline elemental bands configured yet for this family.
                    </td>
                  </tr>
                ) : (
                  activeFamily.baselineElements.map((band) => (
                    <tr
                      key={band.symbol}
                      className={`transition-colors ${
                        isDarkMode ? 'hover:bg-[#151d1a]' : 'hover:bg-[#f2f4f6]'
                      }`}
                    >
                      <td className="p-3 flex items-center gap-2">
                        <span className="font-mono-code font-bold text-[14px]">
                          {band.symbol}
                        </span>
                        <span className={`text-[12px] ${isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'}`}>
                          {band.name}
                        </span>
                        {band.role === 'Required' && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono-code bg-emerald-500/20 text-emerald-400">
                            REQ
                          </span>
                        )}
                      </td>
                      <td className="p-3 font-mono-code">
                        {band.rangeMin.toFixed(2)} - {band.rangeMax.toFixed(2)}
                      </td>
                      <td className={`p-3 ${isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'}`}>
                        {band.spectraSupport.toLocaleString()}
                      </td>
                      <td className="p-3 w-1/3">
                        <div
                          className={`w-full h-2.5 rounded-full overflow-hidden ${
                            isDarkMode ? 'bg-[#2e3733]' : 'bg-[#e0e3e5]'
                          }`}
                        >
                          <div
                            className={`h-full rounded-full ${
                              band.role === 'Required'
                                ? isDarkMode
                                  ? 'bg-[#00ffcc]'
                                  : 'bg-[#006b5b]'
                                : 'bg-[#717974]'
                            }`}
                            style={{
                              marginLeft: `${band.barOffsetPct}%`,
                              width: `${band.barWidthPct}%`,
                            }}
                          />
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Lower Grid: Ratio Gates & Candidate Components */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Ratio Gates Card */}
          <div
            className={`rounded-xl border shadow-sm p-5 transition-colors ${
              isDarkMode
                ? 'bg-[#07100d] border-[#3a4a44]'
                : 'bg-white border-[#c0c8c2]'
            }`}
          >
            <div className="flex justify-between items-center mb-3 pb-2 border-b border-inherit">
              <div className="flex items-center gap-2">
                <span
                  className={`material-symbols-outlined text-[20px] ${
                    isDarkMode ? 'text-[#00ffcc]' : 'text-[#006b5b]'
                  }`}
                >
                  tune
                </span>
                <h3
                  className={`font-semibold text-[15px] ${
                    isDarkMode ? 'text-white' : 'text-[#134231]'
                  }`}
                >
                  Ratio Gates
                </h3>
              </div>
              <button
                onClick={onOpenGateEditor}
                className={`text-[11px] font-bold uppercase tracking-wider hover:underline flex items-center gap-1 ${
                  isDarkMode ? 'text-[#00ffcc]' : 'text-[#006b5b]'
                }`}
              >
                Configure
                <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
              </button>
            </div>

            <div className="space-y-3">
              {activeFamily.ratioGates.length === 0 ? (
                <div className="py-6 text-center text-[12px] opacity-60">
                  <span className="material-symbols-outlined text-[24px] mb-1 block">rule</span>
                  No ratio gates defined for {activeFamily.code}.
                </div>
              ) : (
                activeFamily.ratioGates.map((gate) => (
                  <div
                    key={gate.id}
                    className={`p-2.5 rounded-lg border ${
                      isDarkMode
                        ? 'bg-[#151d1a] border-[#3a4a44]'
                        : 'bg-[#f7f9fb] border-[#c0c8c2]'
                    }`}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-mono-code font-bold text-[13px]">
                        {gate.numerator}/{gate.denominator}
                      </span>
                      <span
                        className={`font-mono-code text-[11px] px-1.5 py-0.5 rounded ${
                          gate.enabled
                            ? isDarkMode
                              ? 'bg-[#00ffcc]/20 text-[#00ffcc]'
                              : 'bg-[#134231] text-white'
                            : 'bg-gray-500/20 text-gray-400'
                        }`}
                      >
                        {gate.min} - {gate.max}
                      </span>
                    </div>
                    <p
                      className={`text-[11.5px] ${
                        isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                      }`}
                    >
                      {gate.rationale}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Candidate Components Card */}
          <div
            className={`rounded-xl border shadow-sm p-5 transition-colors ${
              isDarkMode
                ? 'bg-[#07100d] border-[#3a4a44]'
                : 'bg-white border-[#c0c8c2]'
            }`}
          >
            <div className="flex items-center gap-2 mb-3 pb-2 border-b border-inherit">
              <span
                className={`material-symbols-outlined text-[20px] ${
                  isDarkMode ? 'text-[#00ffcc]' : 'text-[#006b5b]'
                }`}
              >
                category
              </span>
              <h3
                className={`font-semibold text-[15px] ${
                  isDarkMode ? 'text-white' : 'text-[#134231]'
                }`}
              >
                Candidate Components
              </h3>
            </div>

            {activeFamily.candidateComponents.length === 0 ? (
              <div className="py-6 text-center text-[12px] opacity-60">
                <span className="material-symbols-outlined text-[24px] mb-1 block">category</span>
                No components cataloged for {activeFamily.code}.
              </div>
            ) : (
              <ul className="space-y-1.5 text-[13px]">
                {(showAllComponents
                  ? activeFamily.candidateComponents
                  : activeFamily.candidateComponents.slice(0, 3)
                ).map((comp) => (
                  <li
                    key={comp.id}
                    onClick={() => onSelectComponent(comp)}
                    className={`flex items-center gap-2.5 p-1.5 rounded cursor-pointer transition-colors ${
                      isDarkMode ? 'hover:bg-[#151d1a]' : 'hover:bg-[#f2f4f6]'
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        isDarkMode ? 'bg-[#00ffcc]' : 'bg-[#006b5b]'
                      }`}
                    />
                    <span className={`font-medium truncate ${isDarkMode ? 'text-white' : 'text-[#191c1e]'}`}>
                      {comp.name}
                    </span>
                    <span
                      className={`text-[11px] font-mono-code ml-auto shrink-0 ${
                        isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'
                      }`}
                    >
                      {comp.partNumber}
                    </span>
                  </li>
                ))}
              </ul>
            )}

            {activeFamily.candidateComponents.length > 3 && (
              <div className="pt-2 mt-2 border-t border-inherit flex justify-center">
                <button
                  onClick={() => setShowAllComponents(!showAllComponents)}
                  className={`text-[12px] font-semibold flex items-center gap-1 hover:underline ${
                    isDarkMode ? 'text-[#00ffcc]' : 'text-[#006b5b]'
                  }`}
                >
                  {showAllComponents
                    ? 'Show fewer components'
                    : `View all ${activeFamily.candidateComponents.length} components`}
                  <span className="material-symbols-outlined text-[16px]">chevron_right</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
};
