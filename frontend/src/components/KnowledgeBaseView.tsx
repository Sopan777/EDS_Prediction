import React, { useState } from 'react';
import { MaterialFamily, CandidateComponent } from '../types';

interface KnowledgeBaseViewProps {
  isDarkMode: boolean;
  activeFamily?: MaterialFamily | null;
  onSelectFamily: (f: MaterialFamily) => void;
  onOpenGateEditor: () => void;
  onSelectComponent: (comp: CandidateComponent) => void;
  families: MaterialFamily[];
}

const ELEMENT_NAMES: Record<string, string> = {
  Cr: 'Chromium',
  Ni: 'Nickel',
  Mn: 'Manganese',
  Si: 'Silicon',
  Fe: 'Iron',
  Mo: 'Molybdenum',
  Cu: 'Copper',
  Sn: 'Tin',
  Al: 'Aluminium',
  Zn: 'Zinc',
  W: 'Tungsten',
  V: 'Vanadium',
  Ti: 'Titanium',
  Nb: 'Niobium',
  Co: 'Cobalt',
  P: 'Phosphorus',
  S: 'Sulfur',
  Pb: 'Lead',
  Au: 'Gold',
  C: 'Carbon',
  O: 'Oxygen',
  N: 'Nitrogen',
};

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
          className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
          style={{ background: 'var(--color-bg-card)', color: 'var(--color-text-secondary)' }}
        >
          <span className="material-symbols-outlined text-[36px]">menu_book</span>
        </div>
        <h3 className="type-title mb-2" style={{ color: 'var(--color-text-primary)' }}>
          No Material Families in Knowledge Base
        </h3>
        <p className="type-body max-w-md" style={{ color: 'var(--color-text-secondary)' }}>
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
          className="p-4 flex flex-col h-full overflow-hidden transition-colors"
          style={{
            background: 'var(--color-bg-card)',
            boxShadow: 'var(--shadow-card)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--color-border)',
          }}
        >
          {/* Header */}
          <div className="flex justify-between items-center mb-3">
            <h3 className="type-headline" style={{ color: 'var(--color-text-primary)' }}>
              Material Families
            </h3>
            <span className="type-caption type-mono" style={{ color: 'var(--color-text-tertiary)' }}>
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
              className="w-full px-3 py-2 text-[13px] focus:outline-none transition-colors"
              style={{
                background: 'var(--color-bg-base)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text-primary)',
                borderRadius: 'var(--radius-sm)',
              }}
            />
          </div>

          {/* Families list */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {filteredFamilies.length === 0 ? (
              <div className="py-8 text-center type-caption" style={{ color: 'var(--color-text-tertiary)' }}>
                No matching material families
              </div>
            ) : (
              filteredFamilies.map((fam, index) => {
                const isSelected = fam.id === activeFamily.id;
                const staggerClass = `stagger-${Math.min(index + 1, 10)}`;
                return (
                  <div
                    key={fam.id}
                    onClick={() => onSelectFamily(fam)}
                    className={`p-3 cursor-pointer transition-all anim-spring-in ${staggerClass}`}
                    style={{
                      background: isSelected ? 'var(--color-accent-subtle)' : 'transparent',
                      border: '1px solid var(--color-border)',
                      borderLeft: isSelected
                        ? '3px solid var(--color-accent)'
                        : '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-md)',
                    }}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span
                        className="font-mono-code text-[13px] font-bold"
                        style={{ color: isSelected ? 'var(--color-accent)' : 'var(--color-text-secondary)' }}
                      >
                        {fam.code}
                      </span>

                      {fam.status === 'FIRM' ? (
                        <span
                          className="type-caption px-2 py-0.5 font-bold uppercase tracking-wider"
                          style={{
                            color: 'var(--color-pass)',
                            background: 'var(--color-pass-subtle)',
                            borderRadius: 'var(--radius-xl)',
                          }}
                        >
                          FIRM
                        </span>
                      ) : (
                        <span
                          className="type-caption px-2 py-0.5 font-bold uppercase tracking-wider"
                          style={{
                            color: 'var(--color-warn)',
                            background: 'var(--color-warn-subtle)',
                            borderRadius: 'var(--radius-xl)',
                          }}
                        >
                          PROV
                        </span>
                      )}
                    </div>
                    <h4 className="text-[14px] font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                      {fam.name}
                    </h4>
                    <p className="type-caption mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
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
          className="p-6 transition-colors"
          style={{
            background: 'var(--color-bg-card)',
            boxShadow: 'var(--shadow-card)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--color-border)',
          }}
        >
          <div className="flex justify-between items-start">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span
                  className="font-mono-code text-[14px] font-bold px-2 py-0.5"
                  style={{
                    background: 'var(--color-bg-base)',
                    color: 'var(--color-accent)',
                    borderRadius: 'var(--radius-sm)',
                  }}
                >
                  {activeFamily.code}
                </span>

                <span
                  className="px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider flex items-center gap-1"
                  style={{
                    background: 'var(--color-accent)',
                    color: 'var(--color-accent-on)',
                    borderRadius: 'var(--radius-xl)',
                  }}
                >
                  <span className="material-symbols-outlined text-[13px]">verified</span>
                  {activeFamily.status} FAMILY
                </span>
              </div>

              <h2 className="type-display mb-1" style={{ color: 'var(--color-text-primary)' }}>
                {activeFamily.name}
              </h2>
              <p className="type-body flex items-center gap-1.5" style={{ color: 'var(--color-text-secondary)' }}>
                <span className="material-symbols-outlined text-[15px]">info</span>
                Grade hint: {activeFamily.gradeHint}
              </p>
            </div>

            <button
              id="btn-edit-profile"
              onClick={onOpenGateEditor}
              className="press-target px-4 py-2 text-[13px] font-semibold transition-all flex items-center gap-1.5"
              style={{
                background: 'var(--color-accent)',
                color: 'var(--color-accent-on)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              <span className="material-symbols-outlined text-[18px]">tune</span>
              Open Gate Editor
            </button>
          </div>
        </div>

        {/* Elemental Composition Bands Table */}
        <div
          className="overflow-hidden flex flex-col transition-colors"
          style={{
            background: 'var(--color-bg-card)',
            boxShadow: 'var(--shadow-card)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--color-border)',
          }}
        >
          <div
            className="p-4 flex justify-between items-center"
            style={{ borderBottom: '1px solid var(--color-border)' }}
          >
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[20px]" style={{ color: 'var(--color-accent)' }}>
                layers
              </span>
              <h3 className="type-headline" style={{ color: 'var(--color-text-primary)' }}>
                Baseline Elemental Composition
              </h3>
            </div>
            <span className="type-caption type-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              ASTM E1508 Validated
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-[13px]">
              <thead>
                <tr
                  className="text-[11px] font-bold uppercase tracking-wider"
                  style={{
                    background: 'var(--color-bg-base)',
                    borderBottom: '1px solid var(--color-border)',
                    color: 'var(--color-text-tertiary)',
                  }}
                >
                  <th className="p-3">Element</th>
                  <th className="p-3">Expected Range (wt%)</th>
                  <th className="p-3">Spectra Support</th>
                  <th className="p-3">Confidence Range</th>
                </tr>
              </thead>
              <tbody>
                {(!activeFamily.elementBands || activeFamily.elementBands.length === 0) ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center type-caption" style={{ color: 'var(--color-text-tertiary)' }}>
                      No baseline elemental bands configured yet for this family.
                    </td>
                  </tr>
                ) : (
                  activeFamily.elementBands.map((band, rowIdx) => (
                    <tr
                      key={band.element}
                      className="transition-colors"
                      style={{
                        background: rowIdx % 2 === 0 ? 'var(--color-bg-card)' : 'var(--color-bg-base)',
                        cursor: 'pointer',
                        borderBottom: '1px solid var(--color-border)',
                      }}
                      onMouseEnter={(e) => {
                        (e.currentTarget as HTMLTableRowElement).style.background = 'var(--color-accent-subtle)';
                      }}
                      onMouseLeave={(e) => {
                        (e.currentTarget as HTMLTableRowElement).style.background =
                          rowIdx % 2 === 0 ? 'var(--color-bg-card)' : 'var(--color-bg-base)';
                      }}
                    >
                      <td className="p-3 flex items-center gap-2">
                        <span className="font-mono-code font-bold text-[14px]" style={{ color: 'var(--color-text-primary)' }}>
                          {band.element}
                        </span>
                        <span className="type-caption" style={{ color: 'var(--color-text-tertiary)' }}>
                          {ELEMENT_NAMES[band.element] || band.element}
                        </span>
                        {band.role === 'Required' && (
                          <span
                            className="px-1.5 py-0.5 rounded text-[10px] font-mono-code"
                            style={{ background: 'var(--color-pass-subtle)', color: 'var(--color-pass)' }}
                          >
                            REQ
                          </span>
                        )}
                        {band.role === 'Trace' && (
                          <span
                            className="px-1.5 py-0.5 rounded text-[10px] font-mono-code"
                            style={{ background: 'var(--color-warn-subtle)', color: 'var(--color-warn)' }}
                          >
                            TRACE
                          </span>
                        )}
                      </td>
                      <td className="p-3 font-mono-code" style={{ color: 'var(--color-text-primary)' }}>
                        {band.rangeMin.toFixed(2)} - {band.rangeMax.toFixed(2)}
                      </td>
                      <td className="p-3" style={{ color: 'var(--color-text-secondary)' }}>
                        {band.spectraSupport.toLocaleString()}
                      </td>
                      <td className="p-3 w-1/3">
                        <div
                          className="w-full h-2.5 rounded-full overflow-hidden"
                          style={{ background: 'var(--color-border)' }}
                        >
                          <div
                            className="h-full rounded-full"
                            style={{
                              background: band.role === 'Required' ? 'var(--color-accent)' : 'var(--color-text-tertiary)',
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
            className="p-5 transition-colors"
            style={{
              background: 'var(--color-bg-card)',
              boxShadow: 'var(--shadow-card)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--color-border)',
            }}
          >
            <div
              className="flex justify-between items-center mb-3 pb-2"
              style={{ borderBottom: '1px solid var(--color-border)' }}
            >
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[20px]" style={{ color: 'var(--color-accent)' }}>
                  tune
                </span>
                <h3 className="type-headline" style={{ color: 'var(--color-text-primary)' }}>
                  Ratio Gates
                </h3>
              </div>
              <button
                onClick={onOpenGateEditor}
                className="press-target text-[11px] font-bold uppercase tracking-wider flex items-center gap-1"
                style={{ color: 'var(--color-accent)' }}
              >
                Configure
                <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
              </button>
            </div>

            <div className="space-y-3">
              {(!activeFamily.ratioGates || activeFamily.ratioGates.length === 0) ? (
                <div className="py-6 text-center type-caption" style={{ color: 'var(--color-text-tertiary)' }}>
                  <span className="material-symbols-outlined text-[24px] mb-1 block">rule</span>
                  No ratio gates defined for {activeFamily.code}.
                </div>
              ) : (
                activeFamily.ratioGates.map((gate) => (
                  <div
                    key={gate.id}
                    className="p-2.5"
                    style={{
                      background: 'var(--color-bg-base)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-md)',
                    }}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-mono-code font-bold text-[13px]" style={{ color: 'var(--color-text-primary)' }}>
                        {gate.numerator}/{gate.denominator}
                      </span>
                      <span
                        className="font-mono-code text-[11px] px-1.5 py-0.5"
                        style={{
                          background: gate.enabled ? 'var(--color-pass-subtle)' : 'var(--color-bg-card)',
                          color: gate.enabled ? 'var(--color-pass)' : 'var(--color-text-tertiary)',
                          borderRadius: 'var(--radius-xs)',
                        }}
                      >
                        {gate.min} - {gate.max}
                      </span>
                    </div>
                    <p className="type-caption" style={{ color: 'var(--color-text-secondary)' }}>
                      {gate.rationale}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Candidate Components Card */}
          <div
            className="p-5 transition-colors"
            style={{
              background: 'var(--color-bg-card)',
              boxShadow: 'var(--shadow-card)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--color-border)',
            }}
          >
            <div
              className="flex items-center gap-2 mb-3 pb-2"
              style={{ borderBottom: '1px solid var(--color-border)' }}
            >
              <span className="material-symbols-outlined text-[20px]" style={{ color: 'var(--color-accent)' }}>
                category
              </span>
              <h3 className="type-headline" style={{ color: 'var(--color-text-primary)' }}>
                Candidate Components
              </h3>
            </div>

            {(!activeFamily.candidateComponents || activeFamily.candidateComponents.length === 0) ? (
              <div className="py-6 text-center type-caption" style={{ color: 'var(--color-text-tertiary)' }}>
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
                    className="flex items-center gap-2.5 p-1.5 cursor-pointer transition-colors"
                    style={{ borderRadius: 'var(--radius-sm)' }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLLIElement).style.background = 'var(--color-bg-base)';
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLLIElement).style.background = 'transparent';
                    }}
                  >
                    <span
                      className="w-1.5 h-1.5 rounded-full shrink-0"
                      style={{ background: 'var(--color-accent)' }}
                    />
                    <span className="font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>
                      {comp.name}
                    </span>
                    <span
                      className="type-mono type-caption ml-auto shrink-0"
                      style={{ color: 'var(--color-text-tertiary)' }}
                    >
                      {comp.partNumber}
                    </span>
                  </li>
                ))}
              </ul>
            )}

            {activeFamily.candidateComponents.length > 3 && (
              <div
                className="pt-2 mt-2 flex justify-center"
                style={{ borderTop: '1px solid var(--color-border)' }}
              >
                <button
                  onClick={() => setShowAllComponents(!showAllComponents)}
                  className="press-target type-caption font-semibold flex items-center gap-1"
                  style={{ color: 'var(--color-accent)' }}
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
