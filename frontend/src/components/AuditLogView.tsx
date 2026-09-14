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
    link.setAttribute('download', `spectral_lab_audit_log_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div id="audit-log-screen" className="flex flex-col gap-5 h-full">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2
            className={`font-display text-[28px] font-bold tracking-tight ${
              isDarkMode ? 'text-white' : 'text-[#134231]'
            }`}
          >
            System Audit Log
          </h2>
          <p className={`text-[13px] ${isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'}`}>
            Tracking modifications to spectral matching logic, gates, and overrides.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span
            className={`px-3 py-1 rounded-full text-[12px] font-mono-code font-medium border ${
              isDarkMode
                ? 'bg-[#151d1a] border-[#3a4a44] text-[#00ffcc]'
                : 'bg-white border-[#c0c8c2] text-[#134231]'
            }`}
          >
            {auditLogs.length} {auditLogs.length === 1 ? 'change' : 'changes'} recorded
          </span>
          <button
            id="btn-export-csv"
            onClick={handleExportCSV}
            disabled={filteredLogs.length === 0}
            className={`px-3.5 py-1.5 rounded-lg text-[13px] font-semibold flex items-center gap-1.5 shadow-sm transition-all ${
              filteredLogs.length === 0
                ? 'opacity-50 cursor-not-allowed bg-gray-400 text-white'
                : isDarkMode
                ? 'bg-[#00ffcc] text-[#00382b] hover:bg-[#24ffcd]'
                : 'bg-[#134231] text-white hover:bg-[#2d5a47]'
            }`}
          >
            <span className="material-symbols-outlined text-[17px]">download</span>
            Export CSV
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div
        className={`p-4 rounded-xl border shadow-sm flex flex-wrap items-center gap-4 transition-colors ${
          isDarkMode ? 'bg-[#07100d] border-[#3a4a44]' : 'bg-white border-[#c0c8c2]'
        }`}
      >
        {/* Action Type */}
        <div className="flex-1 min-w-[160px]">
          <label className={`block text-[11px] font-bold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'}`}>
            Action Type
          </label>
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className={`w-full py-1.5 px-3 rounded text-[13px] border focus:outline-none ${
              isDarkMode
                ? 'bg-[#151d1a] border-[#3a4a44] text-white focus:border-[#00ffcc]'
                : 'bg-[#f7f9fb] border-[#c0c8c2] text-[#191c1e] focus:border-[#134231]'
            }`}
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
          <label className={`block text-[11px] font-bold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'}`}>
            User / Role
          </label>
          <select
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            className={`w-full py-1.5 px-3 rounded text-[13px] border focus:outline-none ${
              isDarkMode
                ? 'bg-[#151d1a] border-[#3a4a44] text-white focus:border-[#00ffcc]'
                : 'bg-[#f7f9fb] border-[#c0c8c2] text-[#191c1e] focus:border-[#134231]'
            }`}
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
          <label className={`block text-[11px] font-bold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'}`}>
            Material Family
          </label>
          <select
            value={familyFilter}
            onChange={(e) => setFamilyFilter(e.target.value)}
            className={`w-full py-1.5 px-3 rounded text-[13px] border focus:outline-none ${
              isDarkMode
                ? 'bg-[#151d1a] border-[#3a4a44] text-white focus:border-[#00ffcc]'
                : 'bg-[#f7f9fb] border-[#c0c8c2] text-[#191c1e] focus:border-[#134231]'
            }`}
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
            className={`px-3 py-1.5 rounded text-[12px] font-semibold border transition-colors ${
              isDarkMode
                ? 'border-[#3a4a44] text-[#b9cbc2] hover:bg-[#151d1a]'
                : 'border-[#c0c8c2] text-[#414944] hover:bg-[#f2f4f6]'
            }`}
          >
            Reset Filters
          </button>
        </div>
      </div>

      {/* Audit Log Table */}
      <div
        className={`flex-1 rounded-xl border shadow-sm overflow-hidden flex flex-col transition-colors ${
          isDarkMode ? 'bg-[#07100d] border-[#3a4a44]' : 'bg-white border-[#c0c8c2]'
        }`}
      >
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr
                className={`border-b text-[11px] font-bold uppercase tracking-wider ${
                  isDarkMode
                    ? 'bg-[#151d1a] border-[#3a4a44] text-[#83958d]'
                    : 'bg-[#f7f9fb] border-[#c0c8c2] text-[#414944]'
                }`}
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
            <tbody className="divide-y divide-inherit text-[13px]">
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-16 text-center">
                    <div className="flex flex-col items-center justify-center max-w-md mx-auto">
                      <div
                        className={`w-12 h-12 rounded-xl flex items-center justify-center mb-3 ${
                          isDarkMode ? 'bg-[#151d1a] text-[#83958d]' : 'bg-[#f2f4f6] text-[#717974]'
                        }`}
                      >
                        <span className="material-symbols-outlined text-[28px]">receipt_long</span>
                      </div>
                      <h4
                        className={`text-[15px] font-bold mb-1 ${
                          isDarkMode ? 'text-white' : 'text-[#191c1e]'
                        }`}
                      >
                        No Audit Log Records
                      </h4>
                      <p
                        className={`text-[12px] leading-relaxed ${
                          isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                        }`}
                      >
                        Modifications to ratio gates, spectral baseline shifts, and user permission changes will be permanently logged here in real time.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr
                    key={log.id}
                    className={`transition-colors ${
                      isDarkMode ? 'hover:bg-[#151d1a]' : 'hover:bg-[#f2f4f6]'
                    }`}
                  >
                    {/* Timestamp */}
                    <td className="p-3.5 font-mono-code text-[12px] whitespace-nowrap">
                      {log.timestamp}
                    </td>

                    {/* User */}
                    <td className="p-3.5">
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold border shrink-0 ${
                            isDarkMode
                              ? 'bg-[#151d1a] border-[#3a4a44] text-[#00ffcc]'
                              : 'bg-[#eceef0] border-[#c0c8c2] text-[#134231]'
                          }`}
                        >
                          {log.user.slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <span className={`font-medium block leading-tight ${isDarkMode ? 'text-white' : 'text-[#191c1e]'}`}>
                            {log.user}
                          </span>
                          <span className={`text-[11px] block ${isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'}`}>
                            {log.userRole}
                          </span>
                        </div>
                      </div>
                    </td>

                    {/* Action */}
                    <td className="p-3.5">
                      <span className={`font-semibold block ${isDarkMode ? 'text-white' : 'text-[#191c1e]'}`}>
                        {log.action}
                      </span>
                      <span
                        className={`text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded ${
                          log.actionType === 'Gate Edit'
                            ? isDarkMode
                              ? 'bg-[#1a2420] text-[#00ffcc]'
                              : 'bg-[#bcedd4] text-[#002115]'
                            : log.actionType === 'Calibration'
                            ? isDarkMode
                              ? 'bg-[#2c3c51] text-sky-300'
                              : 'bg-sky-100 text-sky-900'
                            : log.actionType === 'Override'
                            ? isDarkMode
                              ? 'bg-amber-950 text-amber-300'
                              : 'bg-amber-100 text-amber-900'
                            : isDarkMode
                            ? 'bg-[#232c28] text-gray-300'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {log.actionType}
                      </span>
                    </td>

                    {/* Family */}
                    <td className="p-3.5">
                      <span
                        className={`font-mono-code font-bold text-[12px] px-2 py-0.5 rounded ${
                          isDarkMode ? 'bg-[#151d1a] text-white' : 'bg-[#f2f4f6] text-[#191c1e]'
                        }`}
                      >
                        {log.familyCode}
                      </span>
                    </td>

                    {/* Change Details */}
                    <td className="p-3.5 font-mono-code text-[12px]">
                      <div className="flex items-center gap-1.5">
                        <span className="line-through opacity-60 text-red-500">
                          {log.changeDetails.from}
                        </span>
                        <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                        <span className="text-emerald-500 font-bold">
                          {log.changeDetails.to}
                        </span>
                      </div>
                    </td>

                    {/* Impact */}
                    <td className="p-3.5">
                      <span
                        className={`px-2.5 py-1 rounded-full text-[11px] font-medium inline-block ${
                          log.impactType === 'positive'
                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                            : log.impactType === 'warning'
                            ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30'
                            : 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border border-gray-500/30'
                        }`}
                      >
                        {log.impactText}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="p-3.5 text-right">
                      <button
                        onClick={() => setSelectedEntry(log)}
                        className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
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
          className={`p-3 border-t flex justify-between items-center text-[12px] ${
            isDarkMode ? 'bg-[#151d1a] border-[#3a4a44] text-[#b9cbc2]' : 'bg-[#f7f9fb] border-[#c0c8c2] text-[#717974]'
          }`}
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
            >
              Previous
            </button>
            <button
              disabled
              className="px-2.5 py-1 rounded border opacity-50 cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Details Modal */}
      {selectedEntry && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div
            className={`w-full max-w-lg rounded-xl border shadow-2xl p-6 transition-colors ${
              isDarkMode ? 'bg-[#0c1512] border-[#3a4a44] text-[#dbe5df]' : 'bg-white border-[#c0c8c2] text-[#191c1e]'
            }`}
          >
            <div className="flex justify-between items-center mb-4 pb-3 border-b border-inherit">
              <h3 className="font-display text-[18px] font-bold">Audit Entry Verification</h3>
              <button
                onClick={() => setSelectedEntry(null)}
                className="p-1 rounded text-gray-400 hover:text-white"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="space-y-3 text-[13px]">
              <div>
                <span className="block text-[11px] font-bold uppercase tracking-wider opacity-60">
                  Event ID
                </span>
                <span className="font-mono-code font-bold">{selectedEntry.id}</span>
              </div>
              <div>
                <span className="block text-[11px] font-bold uppercase tracking-wider opacity-60">
                  User & Role
                </span>
                <span>{selectedEntry.user} ({selectedEntry.userRole})</span>
              </div>
              <div>
                <span className="block text-[11px] font-bold uppercase tracking-wider opacity-60">
                  Action
                </span>
                <span className="font-medium">{selectedEntry.action}</span>
              </div>
              <div>
                <span className="block text-[11px] font-bold uppercase tracking-wider opacity-60">
                  Target Material Family
                </span>
                <span className="font-mono-code font-bold">{selectedEntry.familyCode}</span>
              </div>
              <div>
                <span className="block text-[11px] font-bold uppercase tracking-wider opacity-60">
                  Change Log
                </span>
                <div className={`p-2.5 rounded font-mono-code text-[12px] border ${isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'}`}>
                  <p className="line-through text-red-400">Before: {selectedEntry.changeDetails.from}</p>
                  <p className="text-emerald-400 font-bold mt-1">After: {selectedEntry.changeDetails.to}</p>
                </div>
              </div>
              <div>
                <span className="block text-[11px] font-bold uppercase tracking-wider opacity-60">
                  System Impact
                </span>
                <span className="font-medium text-emerald-500">{selectedEntry.impactText}</span>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setSelectedEntry(null)}
                className={`px-4 py-2 rounded-lg text-[13px] font-semibold ${
                  isDarkMode ? 'bg-[#151d1a] hover:bg-[#232c28] text-white' : 'bg-[#eceef0] hover:bg-[#dfe2e4] text-[#191c1e]'
                }`}
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
