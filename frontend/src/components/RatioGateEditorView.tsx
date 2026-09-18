import React, { useState, useCallback } from 'react';
import { MaterialFamily, RatioGate } from '../types';

interface RatioGateEditorViewProps {
  isDarkMode: boolean;
  activeFamily: MaterialFamily;
  onSaveGates: (familyId: string, updatedGates: RatioGate[]) => void;
  onBack: () => void;
}

interface ValidationMetrics {
  total: number;
  passing: number;
  failing: number;
  topFailing: { grade: string; count: number }[];
  note?: string;
}

export const RatioGateEditorView: React.FC<RatioGateEditorViewProps> = ({
  isDarkMode,
  activeFamily,
  onSaveGates,
  onBack,
}) => {
  const [gates, setGates] = useState<RatioGate[]>(() =>
    activeFamily.ratioGates.map((g) => ({ ...g }))
  );
  const [showAddModal, setShowAddModal] = useState(false);
  const [newGateNumerator, setNewGateNumerator] = useState('Cr');
  const [newGateDenominator, setNewGateDenominator] = useState('Mn');
  const [newGateMin, setNewGateMin] = useState(1.2);
  const [newGateMax, setNewGateMax] = useState(2.8);
  const [newGateRationale, setNewGateRationale] = useState('Suppresses high-manganese variants');

  // Real validation metrics from backend — no synthetic arithmetic
  const [validationMetrics, setValidationMetrics] = useState<ValidationMetrics | null>(null);
  const [validating, setValidating] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Call backend to validate current gates against real reference spectra
  const runValidation = useCallback(() => {
    setValidating(true);
    setValidationError(null);
    fetch('/api/gates/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        family_code: activeFamily.code,
        gates: gates,
      }),
    })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: ValidationMetrics) => setValidationMetrics(data))
      .catch((err) => setValidationError(err.message || 'Validation failed'))
      .finally(() => setValidating(false));
  }, [activeFamily.code, gates]);

  const handleToggleGate = (id: string) => {
    setGates((prev) =>
      prev.map((g) => (g.id === id ? { ...g, enabled: !g.enabled } : g))
    );
  };

  const handleUpdateGate = (id: string, updates: Partial<RatioGate>) => {
    setGates((prev) =>
      prev.map((g) => (g.id === id ? { ...g, ...updates } : g))
    );
  };

  const handleDeleteGate = (id: string) => {
    setGates((prev) => prev.filter((g) => g.id !== id));
  };

  const handleAddGate = (e: React.FormEvent) => {
    e.preventDefault();
    const newId = `gate-${Date.now()}`;
    const newGate: RatioGate = {
      id: newId,
      name: `${newGateNumerator} / ${newGateDenominator}`,
      numerator: newGateNumerator,
      denominator: newGateDenominator,
      min: newGateMin,
      max: newGateMax,
      rationale: newGateRationale,
      enabled: true,
    };
    setGates((prev) => [...prev, newGate]);
    setShowAddModal(false);
    // Clear stale validation — user has changed gates
    setValidationMetrics(null);
  };

  const handleSave = () => {
    onSaveGates(activeFamily.code, gates);
  };

  return (
    <div id="ratio-gate-editor-screen" className="flex gap-6 h-full overflow-hidden">
      {/* Workspace: Gates Editor */}
      <div
        className="flex-1 flex flex-col min-w-0 border overflow-hidden transition-colors"
        style={{
          background: 'var(--color-bg-card)',
          borderColor: 'var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-card)',
        }}
      >
        {/* Editor Top Bar */}
        <div
          className="p-6 border-b flex justify-between items-start"
          style={{
            background: 'var(--color-bg-base)',
            borderColor: 'var(--color-border)',
          }}
        >
          <div>
            <h1 className="type-display" style={{ color: 'var(--color-text-primary)' }}>
              Ratio Gate Editor
            </h1>
            <p className="type-subhead mt-1" style={{ color: 'var(--color-text-secondary)' }}>
              {activeFamily.name} ({activeFamily.code})
            </p>
          </div>

          <button
            id="btn-add-gate-top"
            onClick={() => setShowAddModal(true)}
            className="press-target px-4 py-2 text-[13px] font-semibold flex items-center gap-1.5 shadow-sm transition-all"
            style={{
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-accent)',
              color: 'var(--color-accent-on)',
            }}
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            Add New Gate
          </button>
        </div>

        {/* Scrollable Gates List */}
        <div
          className="flex-1 overflow-y-auto p-6 space-y-4"
          style={{ background: 'var(--color-bg-base)' }}
        >
          {gates.length === 0 ? (
            <div className="py-16 text-center">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-3"
                style={{ background: 'var(--color-bg-card)', color: 'var(--color-text-tertiary)' }}
              >
                <span className="material-symbols-outlined text-[32px]">tune</span>
              </div>
              <h4 className="type-title mb-1" style={{ color: 'var(--color-text-primary)' }}>
                No Ratio Gates Configured
              </h4>
              <p className="type-body max-w-sm mx-auto mb-4" style={{ color: 'var(--color-text-secondary)' }}>
                Define elemental quotient boundaries to discriminate between metallurgical grades in {activeFamily.code}.
              </p>
              <button
                onClick={() => setShowAddModal(true)}
                className="press-target px-4 py-2 text-[13px] font-semibold inline-flex items-center gap-1.5 shadow"
                style={{
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--color-accent)',
                  color: 'var(--color-accent-on)',
                }}
              >
                <span className="material-symbols-outlined text-[17px]">add</span>
                Add First Gate
              </button>
            </div>
          ) : (

            gates.map((gate) => (
            <div
              key={gate.id}
              className="border p-4 flex flex-col gap-4 relative transition-all shadow-sm"
              style={{
                borderRadius: 'var(--radius-lg)',
                background: 'var(--color-bg-card)',
                borderColor: 'var(--color-border)',
                opacity: gate.enabled ? 1 : 0.6,
              }}
            >
              {/* Gate Header with Toggle */}
              <div
                className="flex justify-between items-center border-b pb-2.5"
                style={{ borderColor: 'var(--color-border)' }}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="material-symbols-outlined text-[20px]"
                    style={{ color: 'var(--color-accent)' }}
                  >
                    analytics
                  </span>
                  <h3 className="type-headline" style={{ color: 'var(--color-text-primary)' }}>
                    {gate.name}
                  </h3>
                </div>

                <div className="flex items-center gap-3">
                  <span className="type-caption" style={{ color: gate.enabled ? 'var(--color-pass)' : 'var(--color-text-tertiary)' }}>
                    {gate.enabled ? 'Active' : 'Disabled'}
                  </span>

                  {/* Apple Toggle Switch */}
                  <button
                    type="button"
                    role="switch"
                    aria-checked={gate.enabled}
                    onClick={() => handleToggleGate(gate.id)}
                    className={`toggle-switch ${gate.enabled ? 'on' : ''}`}
                    title={gate.enabled ? 'Disable Gate' : 'Enable Gate'}
                  />

                  <button
                    onClick={() => handleDeleteGate(gate.id)}
                    title="Remove Gate"
                    className="press-target p-1 transition-colors hover:text-red-500"
                    style={{ color: 'var(--color-text-tertiary)' }}
                  >
                    <span className="material-symbols-outlined text-[18px]">delete</span>
                  </button>
                </div>
              </div>

              {/* Range & Rationale Form Fields */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Range Configuration */}
                <div>
                  <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                    Range Configuration
                  </label>
                  <div className="flex items-center gap-2">
                    <div className="flex-1">
                      <span className="type-caption block mb-0.5" style={{ color: 'var(--color-text-tertiary)' }}>
                        Min
                      </span>
                      <input
                        type="number"
                        step="0.01"
                        value={gate.min}
                        onChange={(e) =>
                          handleUpdateGate(gate.id, {
                            min: parseFloat(e.target.value) || 0,
                          })
                        }
                        className="w-full border py-1 px-2.5 font-mono-code text-[13px] focus:outline-none transition-colors"
                        style={{
                          borderRadius: 'var(--radius-md)',
                          background: 'var(--color-bg-base)',
                          borderColor: 'var(--color-border)',
                          color: 'var(--color-text-primary)',
                        }}
                      />
                    </div>
                    <span className="mt-4 text-[16px] font-bold" style={{ color: 'var(--color-text-tertiary)' }}>
                      -
                    </span>
                    <div className="flex-1">
                      <span className="type-caption block mb-0.5" style={{ color: 'var(--color-text-tertiary)' }}>
                        Max
                      </span>
                      <input
                        type="number"
                        step="0.01"
                        value={gate.max}
                        onChange={(e) =>
                          handleUpdateGate(gate.id, {
                            max: parseFloat(e.target.value) || 0,
                          })
                        }
                        className="w-full border py-1 px-2.5 font-mono-code text-[13px] focus:outline-none transition-colors"
                        style={{
                          borderRadius: 'var(--radius-md)',
                          background: 'var(--color-bg-base)',
                          borderColor: 'var(--color-border)',
                          color: 'var(--color-text-primary)',
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* Rationale */}
                <div>
                  <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                    Rationale
                  </label>
                  <input
                    type="text"
                    value={gate.rationale}
                    onChange={(e) =>
                      handleUpdateGate(gate.id, { rationale: e.target.value })
                    }
                    className="w-full mt-4 border py-1.5 px-3 text-[13px] focus:outline-none transition-colors"
                    style={{
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--color-bg-base)',
                      borderColor: 'var(--color-border)',
                      color: 'var(--color-text-primary)',
                    }}
                  />
                </div>
              </div>
            </div>
          )))}

          {/* Click to add new gate hint button */}
          <div
            onClick={() => setShowAddModal(true)}
            className="press-target border-2 border-dashed p-6 flex flex-col items-center justify-center cursor-pointer transition-all"
            style={{
              borderRadius: 'var(--radius-lg)',
              borderColor: 'var(--color-border-strong)',
              background: 'var(--color-bg-card)',
              color: 'var(--color-text-tertiary)',
            }}
          >
            <span className="material-symbols-outlined text-[32px] mb-1">add_circle</span>
            <span className="type-subhead font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              Click to add a new ratio gate
            </span>
          </div>
        </div>

        {/* Footer Actions */}
        <div
          className="p-4 border-t flex justify-end gap-3"
          style={{
            background: 'var(--color-bg-base)',
            borderColor: 'var(--color-border)',
          }}
        >
          <button
            id="btn-discard-gates"
            onClick={onBack}
            className="press-target px-5 py-2 text-[13px] font-semibold border transition-all"
            style={{
              borderRadius: 'var(--radius-md)',
              borderColor: 'var(--color-border)',
              color: 'var(--color-text-secondary)',
              background: 'var(--color-bg-card)',
            }}
          >
            Discard
          </button>
          <button
            id="btn-save-gates"
            onClick={handleSave}
            className="press-target px-5 py-2 text-[13px] font-semibold transition-all shadow-sm"
            style={{
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-accent)',
              color: 'var(--color-accent-on)',
            }}
          >
            Save Changes
          </button>
        </div>
      </div>


      {/* Validation Panel (Right, width 320px) */}
      <div
        className="w-80 shrink-0 border flex flex-col overflow-hidden transition-colors"
        style={{
          background: 'var(--color-bg-card)',
          borderColor: 'var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-card)',
        }}
      >
        <div
          className="p-4 border-b"
          style={{
            background: 'var(--color-bg-base)',
            borderColor: 'var(--color-border)',
          }}
        >
          <h2
            className="type-headline flex items-center gap-2"
            style={{ color: 'var(--color-text-primary)' }}
          >
            <span className="material-symbols-outlined text-[20px]" style={{ color: 'var(--color-accent)' }}>
              rule
            </span>
            Validation Preview
          </h2>
        </div>

        <div className="p-4 flex-1 overflow-y-auto flex flex-col gap-4">
          <p className="text-[12.5px]" style={{ color: 'var(--color-text-secondary)' }}>
            Run the current gate configuration against reference spectrum centroids
            to see pass/fail impact before saving.
          </p>

          {/* Run Validation Button */}
          <button
            onClick={runValidation}
            disabled={validating || gates.length === 0}
            className="press-target w-full py-2.5 text-[13px] font-semibold flex items-center justify-center gap-2 transition-all shadow-sm"
            style={{
              borderRadius: 'var(--radius-md)',
              background: validating || gates.length === 0 ? 'var(--color-border)' : 'var(--color-accent)',
              color: validating || gates.length === 0 ? 'var(--color-text-tertiary)' : 'var(--color-accent-on)',
              cursor: validating || gates.length === 0 ? 'not-allowed' : 'pointer',
            }}
          >
            {validating ? (
              <>
                <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                Validating…
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[16px]">play_arrow</span>
                Run Validation
              </>
            )}
          </button>

          {/* Validation Error */}
          {validationError && (
            <div
              className="p-3 border text-[12px]"
              style={{
                borderRadius: 'var(--radius-md)',
                background: 'var(--color-fail-subtle)',
                borderColor: 'var(--color-fail)',
                color: 'var(--color-fail)',
              }}
            >
              <p className="font-semibold">Validation failed</p>
              <p className="opacity-80 mt-0.5">{validationError}</p>
            </div>
          )}

          {/* Not-yet-run state */}
          {!validationMetrics && !validating && !validationError && (
            <div
              className="p-4 border text-center text-[12px]"
              style={{
                borderRadius: 'var(--radius-md)',
                background: 'var(--color-bg-base)',
                borderColor: 'var(--color-border)',
                color: 'var(--color-text-tertiary)',
              }}
            >
              <span className="material-symbols-outlined text-[28px] block mb-1.5 opacity-40">analytics</span>
              Click "Run Validation" to test these gates against the
              {activeFamily.code} reference spectra from materials.json.
            </div>
          )}

          {/* Real Validation Results */}
          {validationMetrics && (
            <>
              {/* Reference Spectra count */}
              <div
                className="p-4 border"
                style={{
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--color-bg-base)',
                  borderColor: 'var(--color-border)',
                }}
              >
                <div className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                  Reference Spectra Evaluated
                </div>
                <div className="font-display text-[36px] font-bold leading-tight" style={{ color: 'var(--color-text-primary)' }}>
                  {validationMetrics.total.toLocaleString()}
                </div>
              </div>

              {/* Passing / Failing */}
              <div className="space-y-2.5">
                <div
                  className="p-3.5 border flex justify-between items-center"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-pass-subtle)',
                    borderColor: 'var(--color-pass)',
                  }}
                >
                  <div className="flex items-center gap-2 font-semibold text-[14px]" style={{ color: 'var(--color-pass)' }}>
                    <span className="material-symbols-outlined text-[20px]">check_circle</span>
                    <span>Passing</span>
                  </div>
                  <span className="font-mono-code text-[17px] font-bold" style={{ color: 'var(--color-pass)' }}>
                    {validationMetrics.passing.toLocaleString()}
                  </span>
                </div>
                <div
                  className="p-3.5 border flex justify-between items-center"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-fail-subtle)',
                    borderColor: 'var(--color-fail)',
                  }}
                >
                  <div className="flex items-center gap-2 font-semibold text-[14px]" style={{ color: 'var(--color-fail)' }}>
                    <span className="material-symbols-outlined text-[20px]">cancel</span>
                    <span>Failing</span>
                  </div>
                  <span className="font-mono-code text-[17px] font-bold" style={{ color: 'var(--color-fail)' }}>
                    {validationMetrics.failing.toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Top Failing Gates */}
              {validationMetrics.topFailing.length > 0 && (
                <div className="pt-3 border-t" style={{ borderColor: 'var(--color-border)' }}>
                  <h4 className="type-caption mb-2.5" style={{ color: 'var(--color-text-tertiary)' }}>
                    Gates Causing Failures
                  </h4>
                  <ul className="space-y-1.5 text-[13px] font-mono-code">
                    {validationMetrics.topFailing.map((item) => (
                      <li
                        key={item.grade}
                        className="flex justify-between"
                        style={{ color: 'var(--color-text-secondary)' }}
                      >
                        <span>{item.grade}</span>
                        <span className="font-semibold">{item.count}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Note from backend */}
              {validationMetrics.note && (
                <p className="text-[11px] italic" style={{ color: 'var(--color-text-tertiary)' }}>
                  {validationMetrics.note}
                </p>
              )}
            </>
          )}
        </div>
      </div>

      {/* Add New Gate Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center modal-overlay p-4">
          <div className="anim-spring-in w-full max-w-md">
            <div
              className="w-full p-6 border"
              style={{
                background: 'var(--color-bg-card)',
                borderColor: 'var(--color-border)',
                boxShadow: 'var(--shadow-modal)',
                borderRadius: 'var(--radius-xl)',
                color: 'var(--color-text-primary)',
              }}
            >
              <div className="flex justify-between items-center mb-4 pb-3 border-b" style={{ borderColor: 'var(--color-border)' }}>
                <h3 className="type-title" style={{ color: 'var(--color-text-primary)' }}>
                  Add New Ratio Gate
                </h3>
                <button
                  onClick={() => setShowAddModal(false)}
                  className="press-target p-1"
                  style={{ color: 'var(--color-text-tertiary)' }}
                >
                  <span className="material-symbols-outlined">close</span>
                </button>
              </div>

              <form onSubmit={handleAddGate} className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                      Numerator Element
                    </label>
                    <input
                      type="text"
                      value={newGateNumerator}
                      onChange={(e) => setNewGateNumerator(e.target.value.toUpperCase())}
                      className="w-full border p-2 font-mono-code text-[13px] focus:outline-none"
                      style={{
                        borderRadius: 'var(--radius-md)',
                        background: 'var(--color-bg-base)',
                        borderColor: 'var(--color-border)',
                        color: 'var(--color-text-primary)',
                      }}
                      required
                    />
                  </div>
                  <div>
                    <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                      Denominator Element
                    </label>
                    <input
                      type="text"
                      value={newGateDenominator}
                      onChange={(e) => setNewGateDenominator(e.target.value.toUpperCase())}
                      className="w-full border p-2 font-mono-code text-[13px] focus:outline-none"
                      style={{
                        borderRadius: 'var(--radius-md)',
                        background: 'var(--color-bg-base)',
                        borderColor: 'var(--color-border)',
                        color: 'var(--color-text-primary)',
                      }}
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                      Min Value
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={newGateMin}
                      onChange={(e) => setNewGateMin(parseFloat(e.target.value) || 0)}
                      className="w-full border p-2 font-mono-code text-[13px] focus:outline-none"
                      style={{
                        borderRadius: 'var(--radius-md)',
                        background: 'var(--color-bg-base)',
                        borderColor: 'var(--color-border)',
                        color: 'var(--color-text-primary)',
                      }}
                      required
                    />
                  </div>
                  <div>
                    <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                      Max Value
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={newGateMax}
                      onChange={(e) => setNewGateMax(parseFloat(e.target.value) || 0)}
                      className="w-full border p-2 font-mono-code text-[13px] focus:outline-none"
                      style={{
                        borderRadius: 'var(--radius-md)',
                        background: 'var(--color-bg-base)',
                        borderColor: 'var(--color-border)',
                        color: 'var(--color-text-primary)',
                      }}
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                    Metallurgical Rationale
                  </label>
                  <input
                    type="text"
                    value={newGateRationale}
                    onChange={(e) => setNewGateRationale(e.target.value)}
                    className="w-full border p-2 text-[13px] focus:outline-none"
                    style={{
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--color-bg-base)',
                      borderColor: 'var(--color-border)',
                      color: 'var(--color-text-primary)',
                    }}
                    placeholder="e.g., Excludes high-silicon variants"
                    required
                  />
                </div>

                <div className="flex justify-end gap-2 pt-3 border-t" style={{ borderColor: 'var(--color-border)' }}>
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="press-target px-4 py-2 text-[13px] border"
                    style={{
                      borderRadius: 'var(--radius-md)',
                      borderColor: 'var(--color-border)',
                      color: 'var(--color-text-secondary)',
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="press-target px-4 py-2 text-[13px] font-semibold"
                    style={{
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--color-accent)',
                      color: 'var(--color-accent-on)',
                    }}
                  >
                    Add Gate
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
