import React, { useState, useEffect, useCallback } from 'react';
import { AnalysisRecord } from '../types';

interface AnalysisHistoryViewProps {
  isDarkMode: boolean;
}

const DECISION_BADGE: Record<
  string,
  { label: string; icon: string; bgVar: string; colorVar: string }
> = {
  identified: {
    label: 'IDENTIFIED',
    icon: 'check_circle',
    bgVar: 'var(--color-pass-subtle)',
    colorVar: 'var(--color-pass)',
  },
  ambiguous: {
    label: 'AMBIGUOUS',
    icon: 'help',
    bgVar: 'var(--color-warn-subtle)',
    colorVar: 'var(--color-warn)',
  },
  unknown: {
    label: 'UNKNOWN',
    icon: 'question_mark',
    bgVar: 'var(--color-bg-elevated)',
    colorVar: 'var(--color-text-tertiary)',
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

  return (
    <div className="flex flex-col gap-5 h-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="type-display" style={{ color: 'var(--color-text-primary)' }}>
            Analysis History
          </h2>
          <p className="type-subhead mt-1" style={{ color: 'var(--color-text-secondary)' }}>
            All particle microanalysis records stored in the Dhatu Bodh database.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span
            className="px-3 py-1 text-[12px] font-mono-code font-medium border"
            style={{
              borderRadius: 'var(--radius-full)',
              background: 'var(--color-bg-card)',
              borderColor: 'var(--color-border)',
              color: 'var(--color-accent)',
            }}
          >
            {records.length} {records.length === 1 ? 'analysis' : 'analyses'} stored
          </span>
          <button
            onClick={loadHistory}
            className="press-target p-2 border text-[13px] transition-colors"
            style={{
              borderRadius: 'var(--radius-md)',
              borderColor: 'var(--color-border)',
              color: 'var(--color-text-secondary)',
              background: 'var(--color-bg-card)',
            }}
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
          className="border px-3 py-2 text-[13px] flex-1 min-w-[200px] focus:outline-none"
          style={{
            borderRadius: 'var(--radius-md)',
            background: 'var(--color-bg-card)',
            borderColor: 'var(--color-border)',
            color: 'var(--color-text-primary)',
          }}
        />
        <select
          value={decisionFilter}
          onChange={(e) => setDecisionFilter(e.target.value)}
          className="border px-3 py-2 text-[13px] focus:outline-none"
          style={{
            borderRadius: 'var(--radius-md)',
            background: 'var(--color-bg-card)',
            borderColor: 'var(--color-border)',
            color: 'var(--color-text-primary)',
          }}
        >
          <option value="All">All decisions</option>
          <option value="Identified">Identified</option>
          <option value="Ambiguous">Ambiguous</option>
          <option value="Unknown">Unknown</option>
        </select>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto pr-1">
        {loading ? (
          <div className="flex items-center justify-center h-40 gap-3">
            <div
              className="w-8 h-8 rounded-full border-4 border-t-transparent animate-spin"
              style={{ borderColor: 'var(--color-border-strong)', borderTopColor: 'var(--color-accent)' }}
            />
            <span className="type-subhead" style={{ color: 'var(--color-text-tertiary)' }}>
              Loading history…
            </span>
          </div>
        ) : error ? (
          <div
            className="flex items-center gap-3 p-4 border"
            style={{
              borderRadius: 'var(--radius-lg)',
              background: 'var(--color-fail-subtle)',
              borderColor: 'var(--color-fail)',
              color: 'var(--color-fail)',
            }}
          >
            <span className="material-symbols-outlined">error</span>
            <div>
              <p className="font-semibold text-[13px]">Failed to load analysis history</p>
              <p className="text-[12px] opacity-80">{error}</p>
            </div>
            <button
              onClick={loadHistory}
              className="press-target ml-auto underline text-[12px]"
            >
              Retry
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div
            className="flex flex-col items-center justify-center h-52 gap-3 border text-center p-6"
            style={{
              borderRadius: 'var(--radius-xl)',
              background: 'var(--color-bg-card)',
              borderColor: 'var(--color-border)',
              color: 'var(--color-text-tertiary)',
            }}
          >
            <span className="material-symbols-outlined text-[48px] opacity-40">history</span>
            <p className="type-title" style={{ color: 'var(--color-text-primary)' }}>No analyses found</p>
            <p className="type-body" style={{ color: 'var(--color-text-secondary)' }}>
              {records.length === 0
                ? 'Run your first analysis from the Analyzer tab.'
                : 'No results match the current search filter.'}
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-2.5">
            {filtered.map((record, index) => {
              const badge = DECISION_BADGE[record.decision] || DECISION_BADGE.unknown;
              const isHigh = record.compatibilityPct >= 80;
              const isMid = record.compatibilityPct >= 50;
              const compatColor = isHigh ? 'var(--color-pass)' : isMid ? 'var(--color-warn)' : 'var(--color-text-tertiary)';
              const staggerClass = index < 10 ? `anim-slide-up stagger-${index + 1}` : '';

              return (
                <div
                  key={record.id}
                  className={`border p-4 transition-all hover:border-[var(--color-border-strong)] ${staggerClass}`}
                  style={{
                    background: 'var(--color-bg-card)',
                    borderColor: 'var(--color-border)',
                    boxShadow: 'var(--shadow-card)',
                    borderRadius: 'var(--radius-lg)',
                  }}
                >
                  <div className="flex flex-wrap gap-3 items-start justify-between">
                    {/* Left: decision + family */}
                    <div className="flex flex-col gap-1.5">
                      <div className="flex items-center gap-2">
                        <span
                          className="type-caption flex items-center gap-1 px-2.5 py-0.5 rounded-full"
                          style={{
                            background: badge.bgVar,
                            color: badge.colorVar,
                            borderRadius: 'var(--radius-full)',
                          }}
                        >
                          <span className="material-symbols-outlined text-[13px]">{badge.icon}</span>
                          {badge.label}
                        </span>
                        <span
                          className="type-headline"
                          style={{ color: 'var(--color-text-primary)' }}
                        >
                          {record.materialFamily || 'Unclassified Material'}
                        </span>
                        {record.gradeHint && (
                          <span
                            className="text-[12px]"
                            style={{ color: 'var(--color-text-secondary)' }}
                          >
                            — {record.gradeHint}
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-4 text-[12px]">
                        <span
                          className="flex items-center gap-1"
                          style={{ color: 'var(--color-text-tertiary)' }}
                        >
                          <span className="material-symbols-outlined text-[14px]">schedule</span>
                          {record.timestamp}
                        </span>
                        {record.filename && (
                          <span
                            className="flex items-center gap-1"
                            style={{ color: 'var(--color-text-tertiary)' }}
                          >
                            <span className="material-symbols-outlined text-[14px]">description</span>
                            {record.filename}
                          </span>
                        )}
                        <span
                          className="flex items-center gap-1"
                          style={{ color: 'var(--color-text-tertiary)' }}
                        >
                          <span className="material-symbols-outlined text-[14px]">
                            {record.sourceType === 'manual_entry' ? 'edit' : 'upload_file'}
                          </span>
                          {record.sourceType === 'manual_entry' ? 'Manual entry' : 'File upload'}
                        </span>
                      </div>
                    </div>

                    {/* Right: compatibility */}
                    <div className="flex flex-col items-end gap-0.5">
                      <span className="font-display text-[22px] font-bold" style={{ color: compatColor }}>
                        {record.compatibilityPct}%
                      </span>
                      <span className="type-caption" style={{ color: 'var(--color-text-tertiary)' }}>
                        compatibility
                      </span>
                      {record.processingTimeSec != null && (
                        <span className="text-[11px] font-mono-code" style={{ color: 'var(--color-text-tertiary)' }}>
                          {record.processingTimeSec.toFixed(3)}s
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Candidate components */}
                  {record.candidateComponents && record.candidateComponents.length > 0 && (
                    <div className="mt-3 pt-2.5 flex flex-wrap gap-1.5" style={{ borderTop: '1px solid var(--color-border)' }}>
                      {record.candidateComponents.map((c, i) => (
                        <span
                          key={i}
                          className="text-[11px] px-2 py-0.5 border font-mono-code"
                          style={{
                            borderRadius: 'var(--radius-sm)',
                            background: 'var(--color-bg-base)',
                            borderColor: 'var(--color-border)',
                            color: 'var(--color-text-secondary)',
                          }}
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
