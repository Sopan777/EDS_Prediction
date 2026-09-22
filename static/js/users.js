/**
 * static/js/users.js
 * ==================
 * Personnel roster management, role filtering, status toggling, and registration.
 */

function filterUsers() {
  const searchQuery = (document.getElementById('user-search-input')?.value || '').toLowerCase().trim();
  const roleFilter = document.getElementById('user-role-filter')?.value || 'All';

  const rows = document.querySelectorAll('.user-row');
  rows.forEach(row => {
    const name = (row.getAttribute('data-name') || '').toLowerCase();
    const email = (row.getAttribute('data-email') || '').toLowerCase();
    const role = row.getAttribute('data-role') || '';
    const dept = (row.getAttribute('data-dept') || '').toLowerCase();

    const matchesSearch = name.includes(searchQuery) || email.includes(searchQuery) || dept.includes(searchQuery);
    const matchesRole = roleFilter === 'All' || role === roleFilter;

    if (matchesSearch && matchesRole) {
      row.classList.remove('hidden');
    } else {
      row.classList.add('hidden');
    }
  });
}

function openAddUserModal() {
  document.getElementById('add-user-modal').classList.remove('hidden');
}

function closeAddUserModal() {
  document.getElementById('add-user-modal').classList.add('hidden');
}

async function confirmAddUser(event) {
  event.preventDefault();
  const name = document.getElementById('new-user-name').value.trim();
  const email = document.getElementById('new-user-email').value.trim();
  const role = document.getElementById('new-user-role').value;
  const department = document.getElementById('new-user-dept').value;
  const permissions = document.getElementById('new-user-perm').value;

  try {
    const res = await fetch('/api/users', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({ name, email, role, department, permissions }),
    });

    if (!res.ok) {
      alert('Failed to register user.');
      return;
    }

    closeAddUserModal();
    window.location.reload();
  } catch (err) {
    console.error('Error adding user:', err);
    alert('Connection error registering personnel.');
  }
}

async function toggleUserStatus(uid, newStatus) {
  try {
    const res = await fetch(`/api/users/${uid}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({ isActive: newStatus }),
    });

    if (!res.ok) {
      alert('Failed to update user status.');
      return;
    }

    window.location.reload();
  } catch (err) {
    console.error('Error toggling status:', err);
    alert('Connection error updating personnel status.');
  }
}
