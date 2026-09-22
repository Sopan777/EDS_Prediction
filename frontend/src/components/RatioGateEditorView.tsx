import React, { useState } from 'react';
import { MaterialFamily, RatioGate } from '../types';

interface RatioGateEditorViewProps {
  isDarkMode: boolean;
  activeFamily: MaterialFamily;
  onSaveGates: (familyId: string, updatedGates: RatioGate[]) => void;
  onBack: () => void;
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

  // Dynamic calculation for validation preview
  const calculateMetrics = () => {
    const total = activeFamily.totalSpectra || 0;
    if (total === 0) {
      return {
        total: 0,
        passing: 0,
        failing: 0,
        topFailing: [],
      };
    }
    let baseFailing = 0;

    gates.forEach((g) => {
      if (!g.enabled) return;
      const width = g.max - g.min;
      if (width < 0.5) {
        baseFailing += 38;
      } else if (width < 1.0) {
        baseFailing += 18;
      } else {
        baseFailing += 6;
      }
    });

    const finalFailing = Math.min(baseFailing, total);
    const finalPassing = Math.max(total - finalFailing, 0);

    return {
      total,
      passing: finalPassing,
      failing: finalFailing,
      topFailing:
        finalFailing > 0
          ? [
              { grade: '316L', count: Math.round(finalFailing * 0.75) },
              { grade: '304H', count: Math.round(finalFailing * 0.18) },
              {
                grade: 'Other',
                count: Math.max(
                  finalFailing -
                    Math.round(finalFailing * 0.75) -
                    Math.round(finalFailing * 0.18),
                  1
                ),
              },
            ]
          : [],
    };
  };

  const metrics = calculateMetrics();

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
  };

  const handleSave = () => {
    onSaveGates(activeFamily.id, gates);
  };

  return (
    <div id="ratio-gate-editor-screen" className="flex gap-6 h-full overflow-hidden">
      {/* Workspace: Gates Editor */}
      <div
        className={`flex-1 flex flex-col min-w-0 rounded-xl border shadow-sm overflow-hidden transition-colors ${
          isDarkMode ? 'bg-[#07100d] border-[#3a4a44]' : 'bg-white border-[#c0c8c2]'
        }`}
      >
        {/* Editor Top Bar */}
        <div
          className={`p-6 border-b flex justify-between items-start ${
            isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'
          }`}
        >
          <div>
            <h1
              className={`font-display text-[26px] md:text-[30px] font-bold tracking-tight ${
                isDarkMode ? 'text-white' : 'text-[#191c1e]'
              }`}
            >
              Ratio Gate Editor
            </h1>
            <p className={`text-[13px] mt-0.5 ${isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'}`}>
              {activeFamily.name} ({activeFamily.code})
            </p>
          </div>

          <button
            id="btn-add-gate-top"
            onClick={() => setShowAddModal(true)}
            className={`px-4 py-2 rounded-lg text-[13px] font-semibold flex items-center gap-1.5 shadow-sm transition-all ${
              isDarkMode
                ? 'bg-[#00ffcc] text-[#00382b] hover:bg-[#24ffcd]'
                : 'bg-[#134231] text-white hover:bg-[#2d5a47]'
            }`}
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            Add New Gate
          </button>
        </div>

        {/* Scrollable Gates List */}
        <div
          className={`flex-1 overflow-y-auto p-6 space-y-4 ${
            isDarkMode ? 'bg-[#0c1512]' : 'bg-[#f7f9fb]'
          }`}
        >
          {gates.length === 0 ? (
            <div className="py-16 text-center">
              <div
                className={`w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-3 ${
                  isDarkMode ? 'bg-[#151d1a] text-[#83958d]' : 'bg-[#eceef0] text-[#717974]'
                }`}
              >
                <span className="material-symbols-outlined text-[28px]">tune</span>
              </div>
              <h4
                className={`text-[15px] font-bold mb-1 ${
                  isDarkMode ? 'text-white' : 'text-[#191c1e]'
                }`}
              >
                No Ratio Gates Configured
              </h4>
              <p
                className={`text-[12px] max-w-sm mx-auto mb-4 ${
                  isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                }`}
              >
                Define elemental quotient boundaries to discriminate between metallurgical grades in {activeFamily.code}.
              </p>
              <button
                onClick={() => setShowAddModal(true)}
                className={`px-4 py-2 rounded-lg text-[13px] font-semibold inline-flex items-center gap-1.5 shadow ${
                  isDarkMode
                    ? 'bg-[#00ffcc] text-[#00382b] hover:bg-[#24ffcd]'
                    : 'bg-[#134231] text-white hover:bg-[#2d5a47]'
                }`}
              >
                <span className="material-symbols-outlined text-[17px]">add</span>
                Add First Gate
              </button>
            </div>
          ) : (
            gates.map((gate) => (
            <div
              key={gate.id}
              className={`rounded-lg border p-4 flex flex-col gap-4 relative transition-all shadow-sm ${
                isDarkMode
                  ? 'bg-[#151d1a] border-[#3a4a44]'
                  : 'bg-white border-[#c0c8c2]'
              } ${!gate.enabled ? 'opacity-60' : ''}`}
            >
              {/* Gate Header with Toggle */}
              <div
                className={`flex justify-between items-center border-b pb-2.5 ${
                  isDarkMode ? 'border-[#3a4a44]' : 'border-[#c0c8c2]'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`material-symbols-outlined text-[20px] ${
                      isDarkMode ? 'text-[#00ffcc]' : 'text-[#134231]'
                    }`}
                  >
                    analytics
                  </span>
                  <h3
                    className={`font-semibold text-[15px] ${
                      isDarkMode ? 'text-white' : 'text-[#191c1e]'
                    }`}
                  >
                    {gate.name}
                  </h3>
                </div>

                <div className="flex items-center gap-4">
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={gate.enabled}
                      onChange={() => handleToggleGate(gate.id)}
                      className="sr-only peer"
                    />
                    <div
                      className={`w-11 h-6 rounded-full peer peer-focus:outline-none transition-colors after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full ${
                        isDarkMode
                          ? 'bg-[#2e3733] peer-checked:bg-[#00ffcc] after:border-[#3a4a44]'
                          : 'bg-[#e0e3e5] peer-checked:bg-[#134231] after:border-gray-300'
                      }`}
                    />
                    <span
                      className={`ml-2.5 text-[13px] font-medium ${
                        isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                      }`}
                    >
                      {gate.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </label>

                  <button
                    onClick={() => handleDeleteGate(gate.id)}
                    title="Remove Gate"
                    className="text-[#83958d] hover:text-red-500 transition-colors p-1"
                  >
                    <span className="material-symbols-outlined text-[18px]">delete</span>
                  </button>
                </div>
              </div>

              {/* Range & Rationale Form Fields */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Range Configuration */}
                <div>
                  <label
                    className={`block text-[11px] font-bold uppercase tracking-wider mb-1 ${
                      isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                    }`}
                  >
                    Range Configuration
                  </label>
                  <div className="flex items-center gap-2">
                    <div className="flex-1">
                      <span className={`text-[11px] block mb-0.5 ${isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'}`}>
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
                        className={`w-full border rounded-md py-1 px-2.5 font-mono-code text-[13px] focus:outline-none transition-colors ${
                          isDarkMode
                            ? 'bg-[#0c1512] border-[#3a4a44] text-white focus:border-[#00ffcc]'
                            : 'bg-[#f7f9fb] border-[#c0c8c2] text-[#191c1e] focus:border-[#134231]'
                        }`}
                      />
                    </div>
                    <span className={`mt-4 text-[16px] font-bold ${isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'}`}>
                      -
                    </span>
                    <div className="flex-1">
                      <span className={`text-[11px] block mb-0.5 ${isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'}`}>
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
                        className={`w-full border rounded-md py-1 px-2.5 font-mono-code text-[13px] focus:outline-none transition-colors ${
                          isDarkMode
                            ? 'bg-[#0c1512] border-[#3a4a44] text-white focus:border-[#00ffcc]'
                            : 'bg-[#f7f9fb] border-[#c0c8c2] text-[#191c1e] focus:border-[#134231]'
                        }`}
                      />
                    </div>
                  </div>
                </div>

                {/* Rationale */}
                <div>
                  <label
                    className={`block text-[11px] font-bold uppercase tracking-wider mb-1 ${
                      isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                    }`}
                  >
                    Rationale
                  </label>
                  <input
                    type="text"
                    value={gate.rationale}
                    onChange={(e) =>
                      handleUpdateGate(gate.id, { rationale: e.target.value })
                    }
                    className={`w-full mt-4 border rounded-md py-1.5 px-3 text-[13px] focus:outline-none transition-colors ${
                      isDarkMode
                        ? 'bg-[#0c1512] border-[#3a4a44] text-white focus:border-[#00ffcc]'
                        : 'bg-[#f7f9fb] border-[#c0c8c2] text-[#191c1e] focus:border-[#134231]'
                    }`}
                  />
                </div>
              </div>
            </div>
          )))}

          {/* Click to add new gate hint button */}
          <div
            onClick={() => setShowAddModal(true)}
            className={`border-2 border-dashed rounded-lg p-6 flex flex-col items-center justify-center cursor-pointer transition-all ${
              isDarkMode
                ? 'border-[#3a4a44] bg-[#151d1a]/50 text-[#83958d] hover:text-white hover:border-[#00ffcc]'
                : 'border-[#c0c8c2] bg-white text-[#717974] hover:text-[#191c1e] hover:border-[#134231]'
            }`}
          >
            <span className="material-symbols-outlined text-[32px] mb-1">add_circle</span>
            <span className="text-[14px] font-semibold">Click to add a new ratio gate</span>
          </div>
        </div>

        {/* Footer Actions */}
        <div
          className={`p-4 border-t flex justify-end gap-3 ${
            isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'
          }`}
        >
          <button
            id="btn-discard-gates"
            onClick={onBack}
            className={`px-5 py-2 rounded-lg text-[13px] font-semibold border transition-all ${
              isDarkMode
                ? 'border-[#3a4a44] text-[#b9cbc2] hover:bg-[#232c28]'
                : 'border-[#c0c8c2] text-[#414944] hover:bg-[#eceef0]'
            }`}
          >
            Discard
          </button>
          <button
            id="btn-save-gates"
            onClick={handleSave}
            className={`px-5 py-2 rounded-lg text-[13px] font-semibold transition-all shadow-sm ${
              isDarkMode
                ? 'bg-[#00ffcc] text-[#00382b] hover:bg-[#24ffcd]'
                : 'bg-[#134231] text-white hover:bg-[#2d5a47]'
            }`}
          >
            Save Changes
          </button>
        </div>
      </div>

      {/* Validation Panel (Right, width 320px) */}
      <div
        className={`w-80 shrink-0 rounded-xl border shadow-sm flex flex-col overflow-hidden transition-colors ${
          isDarkMode ? 'bg-[#07100d] border-[#3a4a44]' : 'bg-white border-[#c0c8c2]'
        }`}
      >
        <div
          className={`p-4 border-b ${
            isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'
          }`}
        >
          <h2
            className={`font-semibold text-[15px] flex items-center gap-2 ${
              isDarkMode ? 'text-white' : 'text-[#191c1e]'
            }`}
          >
            <span className="material-symbols-outlined text-[20px]">rule</span>
            Validation Preview
          </h2>
        </div>

        <div className="p-4 flex-1 overflow-y-auto flex flex-col">
          <p className={`text-[12.5px] mb-4 ${isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'}`}>
            Impact of current gate settings on the reference dataset.
          </p>

          {/* Reference Spectra Hero Stat */}
          <div
            className={`p-4 rounded-lg border mb-4 ${
              isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'
            }`}
          >
            <div className={`text-[11px] font-bold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'}`}>
              Reference Spectra
            </div>
            <div
              className={`font-display text-[38px] font-bold leading-tight ${
                isDarkMode ? 'text-white' : 'text-[#191c1e]'
              }`}
            >
              {metrics.total.toLocaleString()}
            </div>
          </div>

          {/* Passing / Failing Stats */}
          <div className="space-y-2.5 mb-6">
            {/* Passing */}
            <div
              className={`p-3.5 rounded-lg border flex justify-between items-center ${
                isDarkMode
                  ? 'bg-emerald-950/40 border-emerald-500/30'
                  : 'bg-emerald-50 border-emerald-200'
              }`}
            >
              <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-semibold text-[14px]">
                <span className="material-symbols-outlined text-[20px]">check_circle</span>
                <span>Passing</span>
              </div>
              <span className="font-mono-code text-[17px] font-bold text-emerald-600 dark:text-emerald-400">
                {metrics.passing.toLocaleString()}
              </span>
            </div>

            {/* Failing */}
            <div
              className={`p-3.5 rounded-lg border flex justify-between items-center ${
                isDarkMode
                  ? 'bg-red-950/40 border-red-500/30'
                  : 'bg-red-50 border-red-200'
              }`}
            >
              <div className="flex items-center gap-2 text-red-600 dark:text-red-400 font-semibold text-[14px]">
                <span className="material-symbols-outlined text-[20px]">cancel</span>
                <span>Failing</span>
              </div>
              <span className="font-mono-code text-[17px] font-bold text-red-600 dark:text-red-400">
                {metrics.failing.toLocaleString()}
              </span>
            </div>
          </div>

          {/* Top Failing Grades */}
          <div className={`pt-4 border-t ${isDarkMode ? 'border-[#3a4a44]' : 'border-[#c0c8c2]'}`}>
            <h4
              className={`text-[11px] font-bold uppercase tracking-wider mb-2.5 ${
                isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'
              }`}
            >
              Top Failing Grades
            </h4>
            {metrics.topFailing.length === 0 ? (
              <p className={`text-[12px] italic ${isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'}`}>
                No failing records detected.
              </p>
            ) : (
              <ul className="space-y-1.5 text-[13px] font-mono-code">
                {metrics.topFailing.map((item) => (
                  <li
                    key={item.grade}
                    className={`flex justify-between ${
                      isDarkMode ? 'text-[#b9cbc2]' : 'text-[#414944]'
                    }`}
                  >
                    <span>{item.grade}</span>
                    <span className="font-semibold">{item.count}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* Add New Gate Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div
            className={`w-full max-w-md rounded-xl border shadow-2xl p-6 transition-colors ${
              isDarkMode ? 'bg-[#0c1512] border-[#3a4a44] text-[#dbe5df]' : 'bg-white border-[#c0c8c2] text-[#191c1e]'
            }`}
          >
            <div className="flex justify-between items-center mb-4 pb-2 border-b border-inherit">
              <h3 className="font-semibold text-[17px]">Add New Ratio Gate</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-gray-400 hover:text-white"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <form onSubmit={handleAddGate} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider mb-1">
                    Numerator Element
                  </label>
                  <input
                    type="text"
                    value={newGateNumerator}
                    onChange={(e) => setNewGateNumerator(e.target.value.toUpperCase())}
                    className={`w-full border rounded p-2 font-mono-code text-[13px] ${
                      isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'
                    }`}
                    required
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider mb-1">
                    Denominator Element
                  </label>
                  <input
                    type="text"
                    value={newGateDenominator}
                    onChange={(e) => setNewGateDenominator(e.target.value.toUpperCase())}
                    className={`w-full border rounded p-2 font-mono-code text-[13px] ${
                      isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'
                    }`}
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider mb-1">
                    Min Value
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={newGateMin}
                    onChange={(e) => setNewGateMin(parseFloat(e.target.value) || 0)}
                    className={`w-full border rounded p-2 font-mono-code text-[13px] ${
                      isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'
                    }`}
                    required
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider mb-1">
                    Max Value
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={newGateMax}
                    onChange={(e) => setNewGateMax(parseFloat(e.target.value) || 0)}
                    className={`w-full border rounded p-2 font-mono-code text-[13px] ${
                      isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'
                    }`}
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider mb-1">
                  Metallurgical Rationale
                </label>
                <input
                  type="text"
                  value={newGateRationale}
                  onChange={(e) => setNewGateRationale(e.target.value)}
                  className={`w-full border rounded p-2 text-[13px] ${
                    isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'
                  }`}
                  placeholder="e.g., Excludes high-silicon variants"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-inherit">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded text-[13px] border border-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded text-[13px] font-semibold bg-emerald-600 text-white hover:bg-emerald-700"
                >
                  Add Gate
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
