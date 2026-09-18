import React, { useState } from 'react';
import { AuditLogEntry } from '../types';

interface AuditLogViewProps {
  isDarkMode: boolean;
  auditLogs: AuditLogEntry[];
}

export const AuditLogView: React.FC<AuditLogViewProps> = ({
  isDarkMode,
  auditLogs,
}) => {
  const [actionFilter, setActionFilter] = useState('All');
  const [userFilter, setUserFilter] = useState('All');
  const [familyFilter, setFamilyFilter] = useState('All');
  const [selectedEntry, setSelectedEntry] = useState<AuditLogEntry | null>(null);

  const availableUsers = Array.from(new Set(auditLogs.map((l) => l.user)));

  const filteredLogs = auditLogs.filter((entry) => {
    if (actionFilter !== 'All' && entry.actionType !== actionFilter) return false;
    if (userFilter !== 'All' && !entry.user.includes(userFilter)) return false;
    if (familyFilter !== 'All' && entry.familyCode !== familyFilter && entry.familyCode !== 'All')
      return false;
    return true;
  });

  const handleExportCSV = () => {
    const headers = ['Timestamp', 'User', 'Role', 'Action', 'Action Type', 'Family', 'From', 'To', 'Impact'];
    const rows = filteredLogs.map((log) => [
      log.timestamp,
      log.user,
      log.userRole,
      `"${log.action.replace(/"/g, '""')}"`,
      log.actionType,
      log.familyCode,
      `"${log.changeDetails.from}"`,
      `"${log.changeDetails.to}"`,
      `"${log.impactText}"`,
    ]);

    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `dhatu_bodh_audit_log_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div id="audit-log-screen" className="flex flex-col gap-5 h-full">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="type-display" style={{ color: 'var(--color-text-primary)' }}>
            System Audit Log
          </h2>
          <p className="type-subhead mt-1" style={{ color: 'var(--color-text-secondary)' }}>
            Immutable trace of modifications to spectral matching logic, gates, and overrides.
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
            {auditLogs.length} {auditLogs.length === 1 ? 'change' : 'changes'} recorded
          </span>
          <button
            id="btn-export-csv"
            onClick={handleExportCSV}
            disabled={filteredLogs.length === 0}
            className="press-target px-3.5 py-1.5 text-[13px] font-semibold flex items-center gap-1.5 shadow-sm transition-all"
            style={{
              borderRadius: 'var(--radius-md)',
              background: filteredLogs.length === 0 ? 'var(--color-border)' : 'var(--color-accent)',
              color: filteredLogs.length === 0 ? 'var(--color-text-tertiary)' : 'var(--color-accent-on)',
              cursor: filteredLogs.length === 0 ? 'not-allowed' : 'pointer',
            }}
          >
            <span className="material-symbols-outlined text-[17px]">download</span>
            Export CSV
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div
        className="p-4 border flex flex-wrap items-center gap-4 transition-colors"
        style={{
          background: 'var(--color-bg-card)',
          borderColor: 'var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-card)',
        }}
      >
        {/* Action Type */}
        <div className="flex-1 min-w-[160px]">
          <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
            Action Type
          </label>
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="w-full py-1.5 px-3 border text-[13px] focus:outline-none"
            style={{
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-bg-base)',
              borderColor: 'var(--color-border)',
              color: 'var(--color-text-primary)',
            }}
          >
            <option value="All">All Actions</option>
            <option value="Gate Edit">Gate Edit</option>
            <option value="Knowledge Base Update">Knowledge Base Update</option>
            <option value="Calibration">Calibration</option>
            <option value="Override">Override</option>
          </select>
        </div>

        {/* User / Role */}
        <div className="flex-1 min-w-[160px]">
          <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
            User / Role
          </label>
          <select
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            className="w-full py-1.5 px-3 border text-[13px] focus:outline-none"
            style={{
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-bg-base)',
              borderColor: 'var(--color-border)',
              color: 'var(--color-text-primary)',
            }}
          >
            <option value="All">All Users</option>
            {availableUsers.map((u) => (
              <option key={u} value={u}>
                {u}
              </option>
            ))}
          </select>
        </div>

        {/* Material Family */}
        <div className="flex-1 min-w-[160px]">
          <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
            Material Family
          </label>
          <select
            value={familyFilter}
            onChange={(e) => setFamilyFilter(e.target.value)}
            className="w-full py-1.5 px-3 border text-[13px] focus:outline-none"
            style={{
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-bg-base)',
              borderColor: 'var(--color-border)',
              color: 'var(--color-text-primary)',
            }}
          >
            <option value="All">All Families</option>
            <option value="F4">F4 (Austenitic)</option>
            <option value="F1a">F1a (Low-alloy)</option>
            <option value="F6a">F6a (Bronze)</option>
            <option value="F2b">F2b (Martensitic)</option>
          </select>
        </div>

        {/* Reset Filter button */}
        <div className="flex items-end self-end">
          <button
            onClick={() => {
              setActionFilter('All');
              setUserFilter('All');
              setFamilyFilter('All');
            }}
            className="press-target px-3 py-1.5 text-[12px] font-semibold border transition-colors"
            style={{
              borderRadius: 'var(--radius-md)',
              borderColor: 'var(--color-border)',
              background: 'var(--color-bg-base)',
              color: 'var(--color-text-secondary)',
            }}
          >
            Reset Filters
          </button>
        </div>
      </div>

      {/* Audit Log Table */}
      <div
        className="flex-1 border overflow-hidden flex flex-col transition-colors"
        style={{
          background: 'var(--color-bg-card)',
          borderColor: 'var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-card)',
        }}
      >
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr
                className="border-b type-caption"
                style={{
                  background: 'var(--color-bg-base)',
                  borderColor: 'var(--color-border)',
                  color: 'var(--color-text-tertiary)',
                }}
              >
                <th className="p-3.5">Timestamp</th>
                <th className="p-3.5">User</th>
                <th className="p-3.5">Action</th>
                <th className="p-3.5">Family</th>
                <th className="p-3.5">Change Details</th>
                <th className="p-3.5">Impact</th>
                <th className="p-3.5 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y text-[13px]" style={{ borderColor: 'var(--color-border)' }}>
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-16 text-center">
                    <div className="flex flex-col items-center justify-center max-w-md mx-auto">
                      <div
                        className="w-12 h-12 rounded-xl flex items-center justify-center mb-3"
                        style={{ background: 'var(--color-bg-base)', color: 'var(--color-text-tertiary)' }}
                      >
                        <span className="material-symbols-outlined text-[28px]">receipt_long</span>
                      </div>
                      <h4 className="type-headline mb-1" style={{ color: 'var(--color-text-primary)' }}>
                        No Audit Log Records
                      </h4>
                      <p className="type-body leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
                        Modifications to ratio gates, spectral baseline shifts, and user permission changes will be permanently logged here in real time.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr
                    key={log.id}
                    className="transition-colors hover:bg-[var(--color-border)]/20"
                    style={{ borderColor: 'var(--color-border)' }}
                  >
                    {/* Timestamp */}
                    <td className="p-3.5 font-mono-code text-[12px] whitespace-nowrap" style={{ color: 'var(--color-text-secondary)' }}>
                      {log.timestamp}
                    </td>

                    {/* User */}
                    <td className="p-3.5">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold border shrink-0"
                          style={{
                            background: 'var(--color-accent-subtle)',
                            borderColor: 'var(--color-accent)',
                            color: 'var(--color-accent)',
                          }}
                        >
                          {log.user.slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <span className="font-medium block leading-tight" style={{ color: 'var(--color-text-primary)' }}>
                            {log.user}
                          </span>
                          <span className="type-caption block" style={{ color: 'var(--color-text-tertiary)' }}>
                            {log.userRole}
                          </span>
                        </div>
                      </div>
                    </td>

                    {/* Action */}
                    <td className="p-3.5">
                      <span className="font-semibold block" style={{ color: 'var(--color-text-primary)' }}>
                        {log.action}
                      </span>
                      <span
                        className="type-caption px-2 py-0.5 rounded-full inline-block mt-0.5"
                        style={{
                          borderRadius: 'var(--radius-full)',
                          background:
                            log.actionType === 'Gate Edit'
                              ? 'var(--color-accent-subtle)'
                              : log.actionType === 'Calibration'
                              ? 'var(--color-pass-subtle)'
                              : log.actionType === 'Override'
                              ? 'var(--color-warn-subtle)'
                              : 'var(--color-bg-base)',
                          color:
                            log.actionType === 'Gate Edit'
                              ? 'var(--color-accent)'
                              : log.actionType === 'Calibration'
                              ? 'var(--color-pass)'
                              : log.actionType === 'Override'
                              ? 'var(--color-warn)'
                              : 'var(--color-text-secondary)',
                        }}
                      >
                        {log.actionType}
                      </span>
                    </td>

                    {/* Family */}
                    <td className="p-3.5">
                      <span
                        className="font-mono-code font-bold text-[12px] px-2 py-0.5 border"
                        style={{
                          borderRadius: 'var(--radius-sm)',
                          background: 'var(--color-bg-base)',
                          borderColor: 'var(--color-border)',
                          color: 'var(--color-text-primary)',
                        }}
                      >
                        {log.familyCode}
                      </span>
                    </td>

                    {/* Change Details */}
                    <td className="p-3.5 font-mono-code text-[12px]">
                      <div className="flex items-center gap-1.5">
                        <span className="line-through opacity-60" style={{ color: 'var(--color-fail)' }}>
                          {log.changeDetails.from}
                        </span>
                        <span className="material-symbols-outlined text-[14px]" style={{ color: 'var(--color-text-tertiary)' }}>
                          arrow_forward
                        </span>
                        <span className="font-bold" style={{ color: 'var(--color-pass)' }}>
                          {log.changeDetails.to}
                        </span>
                      </div>
                    </td>

                    {/* Impact */}
                    <td className="p-3.5">
                      <span
                        className="type-caption px-2.5 py-1 rounded-full inline-block border"
                        style={{
                          borderRadius: 'var(--radius-full)',
                          background:
                            log.impactType === 'positive'
                              ? 'var(--color-pass-subtle)'
                              : log.impactType === 'warning'
                              ? 'var(--color-warn-subtle)'
                              : 'var(--color-bg-base)',
                          borderColor:
                            log.impactType === 'positive'
                              ? 'var(--color-pass)'
                              : log.impactType === 'warning'
                              ? 'var(--color-warn)'
                              : 'var(--color-border)',
                          color:
                            log.impactType === 'positive'
                              ? 'var(--color-pass)'
                              : log.impactType === 'warning'
                              ? 'var(--color-warn)'
                              : 'var(--color-text-secondary)',
                        }}
                      >
                        {log.impactText}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="p-3.5 text-right">
                      <button
                        onClick={() => setSelectedEntry(log)}
                        className="press-target p-1 rounded transition-colors"
                        style={{ color: 'var(--color-text-secondary)' }}
                        title="View Details"
                      >
                        <span className="material-symbols-outlined text-[18px]">visibility</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div
          className="p-3 border-t flex justify-between items-center text-[12px]"
          style={{
            background: 'var(--color-bg-base)',
            borderColor: 'var(--color-border)',
            color: 'var(--color-text-tertiary)',
          }}
        >
          <span>
            {filteredLogs.length === 0
              ? 'Showing 0 of 0 entries'
              : `Showing 1 to ${filteredLogs.length} of ${auditLogs.length} entries`}
          </span>
          <div className="flex gap-2">
            <button
              disabled
              className="px-2.5 py-1 rounded border opacity-50 cursor-not-allowed"
              style={{ borderColor: 'var(--color-border)' }}
            >
              Previous
            </button>
            <button
              disabled
              className="px-2.5 py-1 rounded border opacity-50 cursor-not-allowed"
              style={{ borderColor: 'var(--color-border)' }}
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Details Modal */}
      {selectedEntry && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center modal-overlay p-4">
          <div className="anim-spring-in w-full max-w-lg">
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
              <div
                className="flex justify-between items-center mb-4 pb-3 border-b"
                style={{ borderColor: 'var(--color-border)' }}
              >
                <h3 className="type-title" style={{ color: 'var(--color-text-primary)' }}>
                  Audit Entry Verification
                </h3>
                <button
                  onClick={() => setSelectedEntry(null)}
                  className="press-target p-1"
                  style={{ color: 'var(--color-text-tertiary)' }}
                >
                  <span className="material-symbols-outlined">close</span>
                </button>
              </div>

              <div className="space-y-3 text-[13px]">
                <div>
                  <span className="type-caption block opacity-60" style={{ color: 'var(--color-text-secondary)' }}>
                    Event ID
                  </span>
                  <span className="font-mono-code font-bold">{selectedEntry.id}</span>
                </div>
                <div>
                  <span className="type-caption block opacity-60" style={{ color: 'var(--color-text-secondary)' }}>
                    User & Role
                  </span>
                  <span>{selectedEntry.user} ({selectedEntry.userRole})</span>
                </div>
                <div>
                  <span className="type-caption block opacity-60" style={{ color: 'var(--color-text-secondary)' }}>
                    Action
                  </span>
                  <span className="font-medium">{selectedEntry.action}</span>
                </div>
                <div>
                  <span className="type-caption block opacity-60" style={{ color: 'var(--color-text-secondary)' }}>
                    Target Material Family
                  </span>
                  <span className="font-mono-code font-bold">{selectedEntry.familyCode}</span>
                </div>
                <div>
                  <span className="type-caption block opacity-60" style={{ color: 'var(--color-text-secondary)' }}>
                    Change Log
                  </span>
                  <div
                    className="p-2.5 rounded font-mono-code text-[12px] border"
                    style={{
                      background: 'var(--color-bg-base)',
                      borderColor: 'var(--color-border)',
                    }}
                  >
                    <p className="line-through" style={{ color: 'var(--color-fail)' }}>
                      Before: {selectedEntry.changeDetails.from}
                    </p>
                    <p className="font-bold mt-1" style={{ color: 'var(--color-pass)' }}>
                      After: {selectedEntry.changeDetails.to}
                    </p>
                  </div>
                </div>
                <div>
                  <span className="type-caption block opacity-60" style={{ color: 'var(--color-text-secondary)' }}>
                    System Impact
                  </span>
                  <span className="font-medium" style={{ color: 'var(--color-pass)' }}>
                    {selectedEntry.impactText}
                  </span>
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setSelectedEntry(null)}
                  className="press-target px-4 py-2 text-[13px] font-semibold border"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    borderColor: 'var(--color-border)',
                    background: 'var(--color-bg-base)',
                    color: 'var(--color-text-primary)',
                  }}
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
