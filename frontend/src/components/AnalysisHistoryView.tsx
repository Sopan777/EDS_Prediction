import React, { useState, useEffect, useCallback } from 'react';
import { AnalysisRecord } from '../types';

interface AnalysisHistoryViewProps {
  isDarkMode: boolean;
}

const DECISION_BADGE: Record<string, { label: string; bg: string; text: string }> = {
  identified: {
    label: 'IDENTIFIED',
    bg: 'bg-emerald-500/20',
    text: 'text-emerald-400',
  },
  ambiguous: {
    label: 'AMBIGUOUS',
    bg: 'bg-amber-500/20',
    text: 'text-amber-400',
  },
  unknown: {
    label: 'UNKNOWN',
    bg: 'bg-slate-500/20',
    text: 'text-slate-400',
  },
};

export const AnalysisHistoryView: React.FC<AnalysisHistoryViewProps> = ({
  isDarkMode,
}) => {
  const [records, setRecords] = useState<AnalysisRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [decisionFilter, setDecisionFilter] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  const loadHistory = useCallback(() => {
    setLoading(true);
    setError(null);
    fetch('/api/analyses?limit=200')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: AnalysisRecord[]) => {
        setRecords(data);
      })
      .catch((err) => setError(err.message || 'Failed to load analysis history'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const filtered = records.filter((r) => {
    if (decisionFilter !== 'All' && r.decision !== decisionFilter.toLowerCase()) return false;
    if (
      searchQuery &&
      !r.materialFamily?.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !r.filename?.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !r.decision.toLowerCase().includes(searchQuery.toLowerCase())
    )
      return false;
    return true;
  });

  const cardBase = isDarkMode
    ? 'bg-[#151d1a] border-[#3a4a44]'
    : 'bg-white border-[#c0c8c2]';

  return (
    <div className="flex flex-col gap-5 h-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2
            className={`font-display text-[28px] font-bold tracking-tight ${
              isDarkMode ? 'text-white' : 'text-[#134231]'
            }`}
          >
            Analysis History
          </h2>
          <p className={`text-[13px] ${isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'}`}>
            All particle microanalysis results stored in the database.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span
            className={`px-3 py-1 rounded-full text-[12px] font-mono font-medium border ${
              isDarkMode
                ? 'bg-[#151d1a] border-[#3a4a44] text-[#00ffcc]'
                : 'bg-white border-[#c0c8c2] text-[#134231]'
            }`}
          >
            {records.length} {records.length === 1 ? 'analysis' : 'analyses'} stored
          </span>
          <button
            onClick={loadHistory}
            className={`p-2 rounded-lg border text-[13px] transition-colors ${
              isDarkMode
                ? 'border-[#3a4a44] hover:bg-[#1e2e28] text-[#b9cbc2]'
                : 'border-[#c0c8c2] hover:bg-[#f2f4f6] text-[#717974]'
            }`}
            title="Refresh"
          >
            <span className="material-symbols-outlined text-[18px]">refresh</span>
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search by family, filename, decision…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className={`border rounded-lg px-3 py-2 text-[13px] flex-1 min-w-[200px] ${
            isDarkMode
              ? 'bg-[#151d1a] border-[#3a4a44] text-[#dbe5df] placeholder:text-[#5a6a64]'
              : 'bg-white border-[#c0c8c2] text-[#191c1e] placeholder:text-[#9aa3a0]'
          }`}
        />
        <select
          value={decisionFilter}
          onChange={(e) => setDecisionFilter(e.target.value)}
          className={`border rounded-lg px-3 py-2 text-[13px] ${
            isDarkMode
              ? 'bg-[#151d1a] border-[#3a4a44] text-[#dbe5df]'
              : 'bg-white border-[#c0c8c2] text-[#191c1e]'
          }`}
        >
          <option value="All">All decisions</option>
          <option value="Identified">Identified</option>
          <option value="Ambiguous">Ambiguous</option>
          <option value="Unknown">Unknown</option>
        </select>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto rounded-xl">
        {loading ? (
          <div className="flex items-center justify-center h-40 gap-3">
            <div
              className={`w-8 h-8 rounded-full border-4 border-t-transparent animate-spin ${
                isDarkMode ? 'border-[#00ffcc]' : 'border-[#134231]'
              }`}
            />
            <span className={`text-[13px] ${isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'}`}>
              Loading history…
            </span>
          </div>
        ) : error ? (
          <div
            className={`flex items-center gap-3 p-4 rounded-xl border ${
              isDarkMode
                ? 'bg-red-900/20 border-red-800 text-red-300'
                : 'bg-red-50 border-red-200 text-red-700'
            }`}
          >
            <span className="material-symbols-outlined">error</span>
            <div>
              <p className="font-semibold text-[13px]">Failed to load analysis history</p>
              <p className="text-[12px] opacity-80">{error}</p>
            </div>
            <button
              onClick={loadHistory}
              className="ml-auto underline text-[12px]"
            >
              Retry
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div
            className={`flex flex-col items-center justify-center h-48 gap-3 rounded-xl border ${
              isDarkMode
                ? 'bg-[#151d1a] border-[#3a4a44] text-[#b9cbc2]'
                : 'bg-white border-[#c0c8c2] text-[#717974]'
            }`}
          >
            <span className="material-symbols-outlined text-[40px] opacity-30">history</span>
            <p className="text-[14px] font-medium">No analyses found</p>
            <p className="text-[12px] opacity-70">
              {records.length === 0
                ? 'Run your first analysis from the Analyzer tab.'
                : 'No results match the current filter.'}
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {filtered.map((record) => {
              const badge = DECISION_BADGE[record.decision] || DECISION_BADGE.unknown;
              const compatColor =
                record.compatibilityPct >= 80
                  ? 'text-emerald-500'
                  : record.compatibilityPct >= 50
                  ? 'text-amber-500'
                  : 'text-slate-500';

              return (
                <div
                  key={record.id}
                  className={`rounded-xl border p-4 transition-colors ${cardBase}`}
                >
                  <div className="flex flex-wrap gap-3 items-start justify-between">
                    {/* Left: decision + family */}
                    <div className="flex flex-col gap-1.5">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${badge.bg} ${badge.text}`}
                        >
                          {badge.label}
                        </span>
                        <span
                          className={`font-display font-semibold text-[15px] ${
                            isDarkMode ? 'text-white' : 'text-[#134231]'
                          }`}
                        >
                          {record.materialFamily || 'Unclassified Material'}
                        </span>
                        {record.gradeHint && (
                          <span
                            className={`text-[11px] ${
                              isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                            }`}
                          >
                            — {record.gradeHint}
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-3 text-[12px]">
                        <span
                          className={`flex items-center gap-1 ${
                            isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                          }`}
                        >
                          <span className="material-symbols-outlined text-[14px]">schedule</span>
                          {record.timestamp}
                        </span>
                        {record.filename && (
                          <span
                            className={`flex items-center gap-1 ${
                              isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                            }`}
                          >
                            <span className="material-symbols-outlined text-[14px]">description</span>
                            {record.filename}
                          </span>
                        )}
                        <span
                          className={`flex items-center gap-1 ${
                            isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                          }`}
                        >
                          <span className="material-symbols-outlined text-[14px]">
                            {record.sourceType === 'manual_entry' ? 'edit' : 'upload_file'}
                          </span>
                          {record.sourceType === 'manual_entry' ? 'Manual entry' : 'File upload'}
                        </span>
                      </div>
                    </div>

                    {/* Right: compatibility */}
                    <div className="flex flex-col items-end gap-1">
                      <span className={`font-display text-[22px] font-bold ${compatColor}`}>
                        {record.compatibilityPct}%
                      </span>
                      <span
                        className={`text-[11px] ${
                          isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                        }`}
                      >
                        compatibility
                      </span>
                      {record.processingTimeSec != null && (
                        <span
                          className={`text-[11px] font-mono ${
                            isDarkMode ? 'text-[#5a6a64]' : 'text-[#9aa3a0]'
                          }`}
                        >
                          {record.processingTimeSec.toFixed(3)}s
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Candidate components */}
                  {record.candidateComponents && record.candidateComponents.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {record.candidateComponents.map((c, i) => (
                        <span
                          key={i}
                          className={`text-[11px] px-2 py-0.5 rounded border font-mono ${
                            isDarkMode
                              ? 'border-[#3a4a44] text-[#b9cbc2]'
                              : 'border-[#c0c8c2] text-[#717974]'
                          }`}
                        >
                          {typeof c === 'string' ? c : (c as any).name || c}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
