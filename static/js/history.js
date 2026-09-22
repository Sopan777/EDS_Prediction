/**
 * static/js/history.js
 * ====================
 * Filtering and CSV export for System Audit Log screen.
 */

function filterAuditLogs() {
  const actionFilter = document.getElementById('filter-action-type').value;
  const userFilter = document.getElementById('filter-user').value;
  const familyFilter = document.getElementById('filter-family').value;

  const rows = document.querySelectorAll('.audit-row');
  let visibleCount = 0;

  rows.forEach(row => {
    const rowAction = row.getAttribute('data-action');
    const rowUser = row.getAttribute('data-user');
    const rowFamily = row.getAttribute('data-family');

    const matchesAction = actionFilter === 'All' || rowAction === actionFilter;
    const matchesUser = userFilter === 'All' || rowUser === userFilter;
    const matchesFamily = familyFilter === 'All' || rowFamily === familyFilter || (familyFilter !== 'All' && rowFamily === 'All');

    if (matchesAction && matchesUser && matchesFamily) {
      row.classList.remove('hidden');
      visibleCount++;
    } else {
      row.classList.add('hidden');
    }
  });

  const badge = document.getElementById('logs-count-badge');
  if (badge) {
    badge.textContent = `${visibleCount} changes recorded`;
  }
}

function exportAuditLogCSV() {
  const actionFilter = document.getElementById('filter-action-type').value;
  const userFilter = document.getElementById('filter-user').value;
  const familyFilter = document.getElementById('filter-family').value;

  const logs = window.AUDIT_LOGS || [];
  const filtered = logs.filter(log => {
    if (actionFilter !== 'All' && log.actionType !== actionFilter) return false;
    if (userFilter !== 'All' && log.user !== userFilter) return false;
    if (familyFilter !== 'All' && log.familyCode !== familyFilter && log.familyCode !== 'All') return false;
    return true;
  });

  if (filtered.length === 0) {
    alert('No audit logs matching current filter to export.');
    return;
  }

  const headers = ['Timestamp', 'User', 'Role', 'Action', 'Action Type', 'Family', 'From', 'To', 'Impact'];
  const rows = filtered.map(log => [
    log.timestamp,
    log.user,
    log.userRole,
    `"${(log.action || '').replace(/"/g, '""')}"`,
    log.actionType,
    log.familyCode,
    `"${(log.changeDetails?.from || '').replace(/"/g, '""')}"`,
    `"${(log.changeDetails?.to || '').replace(/"/g, '""')}"`,
    log.impactType,
  ]);

  const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `spectral_lab_audit_log_${Date.now()}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
