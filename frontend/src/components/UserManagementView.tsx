import React, { useState } from 'react';
import { UserAccount, RoleDefinition } from '../types';

interface UserManagementViewProps {
  isDarkMode: boolean;
  users: UserAccount[];
  roles: RoleDefinition[];
  onAddUser: (user: UserAccount) => void;
  onUpdateUser: (id: string, updates: Partial<UserAccount>) => void;
  onAddRole: (role: RoleDefinition) => void;
}

export const UserManagementView: React.FC<UserManagementViewProps> = ({
  isDarkMode,
  users,
  roles,
  onAddUser,
  onUpdateUser,
  onAddRole,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('All');
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [showAddRoleModal, setShowAddRoleModal] = useState(false);

  // New user form state
  const [newUserName, setNewUserName] = useState('');
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserRole, setNewUserRole] = useState<UserAccount['role']>('Lab Tech');
  const [newUserDept, setNewUserDept] = useState<UserAccount['department']>('Operations');
  const [newUserPerm, setNewUserPerm] = useState<UserAccount['permissions']>('Read-only');

  // New role form state
  const [newRoleTitle, setNewRoleTitle] = useState('');
  const [newRoleDesc, setNewRoleDesc] = useState('');

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.department.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRole = roleFilter === 'All' || u.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const handleCreateUser = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUserName.trim() || !newUserEmail.trim()) return;

    const initials = newUserName
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);

    const created: UserAccount = {
      id: `user-${Date.now()}`,
      name: newUserName.trim(),
      email: newUserEmail.trim(),
      role: newUserRole,
      department: newUserDept,
      permissions: newUserPerm,
      initials,
      isActive: true,
      lastActive: 'Just now',
    };

    onAddUser(created);
    setNewUserName('');
    setNewUserEmail('');
    setShowAddUserModal(false);
  };

  const handleCreateRole = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRoleTitle.trim()) return;

    const createdRole: RoleDefinition = {
      id: `role-${Date.now()}`,
      title: newRoleTitle.trim(),
      description: newRoleDesc.trim(),
      userCount: 0,
    };

    onAddRole(createdRole);
    setNewRoleTitle('');
    setNewRoleDesc('');
    setShowAddRoleModal(false);
  };

  const activeTechsCount = users.filter((u) => u.role === 'Lab Tech' && u.isActive).length;
  const totalTechsCount = users.filter((u) => u.role === 'Lab Tech').length;
  const metallurgistsCount = users.filter((u) => u.role.includes('Metallurgist')).length;
  const snrMetCount = users.filter((u) => u.role === 'Snr. Metallurgist').length;
  const inactiveCount = users.filter((u) => !u.isActive).length;

  return (
    <div id="user-management-screen" className="flex flex-col gap-5 h-full overflow-y-auto pb-6 pr-1">
      {/* Page Title */}
      <div>
        <h2 className="type-display" style={{ color: 'var(--color-text-primary)' }}>
          User Management
        </h2>
        <p className="type-subhead mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          Manage lab access, personnel roles, and metallurgical editing permissions.
        </p>
      </div>

      {/* 4 Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            title: 'Total Users',
            val: users.length,
            sub: users.length === 0 ? 'No accounts' : `${users.filter((u) => u.isActive).length} active`,
          },
          {
            title: 'Active Lab Techs',
            val: activeTechsCount,
            sub: `Registered: ${totalTechsCount}`,
          },
          {
            title: 'Metallurgists',
            val: metallurgistsCount,
            sub: `Snr. Level: ${snrMetCount}`,
          },
          {
            title: 'Inactive Accounts',
            val: inactiveCount,
            sub: inactiveCount === 0 ? 'All active' : 'Suspended',
          },
        ].map((card, idx) => (
          <div
            key={idx}
            className="p-4 border transition-colors"
            style={{
              background: 'var(--color-bg-card)',
              borderColor: 'var(--color-border)',
              borderRadius: 'var(--radius-lg)',
              boxShadow: 'var(--shadow-card)',
            }}
          >
            <span className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
              {card.title}
            </span>
            <div className="flex items-baseline justify-between">
              <span className="font-display text-[32px] font-bold" style={{ color: 'var(--color-text-primary)' }}>
                {card.val}
              </span>
              <span className="text-[12px] font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                {card.sub}
              </span>
            </div>
          </div>
        ))}
      </div>


      {/* Main Grid: User Table (Left) & Role Definitions (Right) */}
      <div className="grid grid-cols-12 gap-5 flex-1 min-h-0">
        {/* Left: User Table (8 cols on lg) */}
        <div
          className={`col-span-12 lg:col-span-8 rounded-xl border shadow-sm flex flex-col overflow-hidden transition-colors ${
            isDarkMode ? 'bg-[#07100d] border-[#3a4a44]' : 'bg-white border-[#c0c8c2]'
          }`}
        >
          {/* Action Bar */}
          <div
            className={`p-4 border-b flex flex-wrap justify-between items-center gap-3 ${
              isDarkMode ? 'bg-[#151d1a] border-[#3a4a44]' : 'bg-[#f7f9fb] border-[#c0c8c2]'
            }`}
          >
            <div className="flex items-center gap-2.5 flex-1 min-w-[240px]">
              {/* Search */}
              <div className="relative flex-1">
                <span
                  className={`material-symbols-outlined absolute left-2.5 top-1/2 -translate-y-1/2 text-[18px] ${
                    isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'
                  }`}
                >
                  search
                </span>
                <input
                  type="text"
                  placeholder="Filter personnel..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className={`w-full pl-8 pr-3 py-1.5 rounded text-[12px] border focus:outline-none transition-colors ${
                    isDarkMode
                      ? 'bg-[#0c1512] border-[#3a4a44] text-white focus:border-[#00ffcc]'
                      : 'bg-white border-[#c0c8c2] text-[#191c1e] focus:border-[#134231]'
                  }`}
                />
              </div>

              {/* Role filter */}
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className={`py-1.5 px-2.5 rounded text-[12px] border focus:outline-none ${
                  isDarkMode
                    ? 'bg-[#0c1512] border-[#3a4a44] text-white'
                    : 'bg-white border-[#c0c8c2] text-[#191c1e]'
                }`}
              >
                <option value="All">All Roles</option>
                <option value="Snr. Metallurgist">Snr. Metallurgist</option>
                <option value="Lab Tech">Lab Tech</option>
                <option value="Auditor">Auditor</option>
                <option value="Service Acct">Service Acct</option>
                <option value="SysAdmin">SysAdmin</option>
              </select>
            </div>

            {/* Add User CTA */}
            <button
              id="btn-add-new-user"
              onClick={() => setShowAddUserModal(true)}
              className={`px-3.5 py-1.5 rounded-lg text-[13px] font-semibold flex items-center gap-1.5 shadow-sm transition-all ${
                isDarkMode
                  ? 'bg-[#00ffcc] text-[#00382b] hover:bg-[#24ffcd]'
                  : 'bg-[#134231] text-white hover:bg-[#2d5a47]'
              }`}
            >
              <span className="material-symbols-outlined text-[17px]">person_add</span>
              Add New User
            </button>
          </div>

          {/* Table */}
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr
                  className={`border-b text-[11px] font-bold uppercase tracking-wider ${
                    isDarkMode
                      ? 'bg-[#19211e] border-[#3a4a44] text-[#83958d]'
                      : 'bg-[#eceef0] border-[#c0c8c2] text-[#414944]'
                  }`}
                >
                  <th className="p-3.5">User</th>
                  <th className="p-3.5">Role</th>
                  <th className="p-3.5">Department</th>
                  <th className="p-3.5">Permissions</th>
                  <th className="p-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y text-[13px]">
                {filteredUsers.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-16 text-center">
                      <div className="flex flex-col items-center justify-center max-w-sm mx-auto">
                        <div
                          className={`w-12 h-12 rounded-xl flex items-center justify-center mb-3 ${
                            isDarkMode ? 'bg-[#151d1a] text-[#83958d]' : 'bg-[#f2f4f6] text-[#717974]'
                          }`}
                        >
                          <span className="material-symbols-outlined text-[28px]">group_off</span>
                        </div>
                        <h4
                          className={`text-[15px] font-bold mb-1 ${
                            isDarkMode ? 'text-white' : 'text-[#191c1e]'
                          }`}
                        >
                          No Personnel Registered
                        </h4>
                        <p
                          className={`text-[12px] leading-relaxed mb-4 ${
                            isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'
                          }`}
                        >
                          No laboratory technicians or metallurgists found. Register users to assign operational permissions.
                        </p>
                        <button
                          onClick={() => setShowAddUserModal(true)}
                          className={`px-4 py-2 rounded-lg text-[13px] font-semibold flex items-center gap-1.5 shadow-sm transition-all ${
                            isDarkMode
                              ? 'bg-[#00ffcc] text-[#00382b] hover:bg-[#24ffcd]'
                              : 'bg-[#134231] text-white hover:bg-[#2d5a47]'
                          }`}
                        >
                          <span className="material-symbols-outlined text-[17px]">person_add</span>
                          Add First User
                        </button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredUsers.map((user, idx) => (
                    <tr
                      key={user.id}
                      className={`transition-colors ${
                        idx % 2 === 1
                          ? isDarkMode
                            ? 'bg-[#0c1512]/40'
                            : 'bg-[#f7f9fb]/60'
                          : ''
                      } ${isDarkMode ? 'hover:bg-[#151d1a]' : 'hover:bg-[#f2f4f6]'}`}
                    >
                      {/* User info */}
                      <td className="p-3.5">
                        <div className="flex items-center gap-2.5">
                          {user.avatarUrl ? (
                            <img
                              src={user.avatarUrl}
                              alt={user.name}
                              className="w-8 h-8 rounded-full object-cover shrink-0"
                            />
                          ) : (
                            <div
                              className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-[12px] shrink-0 border"
                              style={{
                                background: 'var(--color-accent-subtle)',
                                borderColor: 'var(--color-accent)',
                                color: 'var(--color-accent)',
                              }}
                            >
                              {user.initials || user.name.slice(0, 2)}
                            </div>
                          )}
                          <div className="min-w-0">
                            <span
                              className="font-semibold block truncate"
                              style={{ color: 'var(--color-text-primary)' }}
                            >
                              {user.name}
                            </span>
                            <span
                              className="type-caption block truncate"
                              style={{ color: 'var(--color-text-tertiary)' }}
                            >
                              {user.email}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Role */}
                      <td className="p-3.5">
                        <span
                          className="type-caption px-2 py-0.5 rounded-full inline-block"
                          style={{
                            borderRadius: 'var(--radius-full)',
                            background: 'var(--color-accent-subtle)',
                            color: 'var(--color-accent)',
                          }}
                        >
                          {user.role}
                        </span>
                      </td>

                      {/* Department */}
                      <td className="p-3.5 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                        {user.department}
                      </td>

                      {/* Permissions */}
                      <td className="p-3.5">
                        <span
                          className="font-mono-code text-[11px] px-2 py-0.5 rounded border"
                          style={{
                            borderRadius: 'var(--radius-sm)',
                            background:
                              user.permissions === 'Full Edit'
                                ? 'var(--color-pass-subtle)'
                                : user.permissions === 'System Execution'
                                ? 'var(--color-warn-subtle)'
                                : 'var(--color-bg-base)',
                            borderColor:
                              user.permissions === 'Full Edit'
                                ? 'var(--color-pass)'
                                : user.permissions === 'System Execution'
                                ? 'var(--color-warn)'
                                : 'var(--color-border)',
                            color:
                              user.permissions === 'Full Edit'
                                ? 'var(--color-pass)'
                                : user.permissions === 'System Execution'
                                ? 'var(--color-warn)'
                                : 'var(--color-text-secondary)',
                          }}
                        >
                          {user.permissions}
                        </span>
                      </td>


                      {/* Actions */}
                      <td className="p-3.5 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => {
                              onUpdateUser(user.id, { isActive: !user.isActive });
                            }}
                            className={`p-1 rounded transition-colors ${
                              user.isActive
                                ? 'hover:bg-red-100 dark:hover:bg-red-900/40 text-gray-400 hover:text-red-500'
                                : 'text-emerald-500'
                            }`}
                            title={user.isActive ? 'Suspend User' : 'Activate User'}
                          >
                            <span className="material-symbols-outlined text-[17px]">
                              {user.isActive ? 'block' : 'check_circle'}
                            </span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Table pagination */}
          <div
            className={`p-3 border-t flex justify-between items-center text-[12px] ${
              isDarkMode ? 'bg-[#151d1a] border-[#3a4a44] text-[#b9cbc2]' : 'bg-[#f7f9fb] border-[#c0c8c2] text-[#717974]'
            }`}
          >
            <span>
              {filteredUsers.length === 0
                ? 'Showing 0 of 0 lab personnel'
                : `Showing 1 to ${filteredUsers.length} of ${users.length} lab personnel`}
            </span>
            <div className="flex gap-1.5">
              <button disabled className="px-2.5 py-1 rounded border opacity-50 cursor-not-allowed">
                Prev
              </button>
              <button disabled className="px-2.5 py-1 rounded border opacity-50 cursor-not-allowed">
                Next
              </button>
            </div>
          </div>
        </div>

        {/* Right: Role Definitions (4 cols on lg) */}
        <div
          className={`col-span-12 lg:col-span-4 rounded-xl border shadow-sm p-5 flex flex-col transition-colors ${
            isDarkMode ? 'bg-[#07100d] border-[#3a4a44]' : 'bg-white border-[#c0c8c2]'
          }`}
        >
          <div className="flex justify-between items-center mb-4 pb-2 border-b border-inherit">
            <h3
              className={`font-semibold text-[16px] ${
                isDarkMode ? 'text-white' : 'text-[#134231]'
              }`}
            >
              Role Definitions
            </h3>
            <span className={`text-[11px] font-mono-code ${isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'}`}>
              RBAC Active
            </span>
          </div>

          <div className="space-y-3 flex-1 overflow-y-auto">
            {roles.map((role) => {
              const countForRole = users.filter((u) => u.role === role.title).length;
              return (
                <div
                  key={role.id}
                  className={`p-3 rounded-lg border transition-all ${
                    isDarkMode
                      ? 'bg-[#151d1a] border-[#3a4a44]'
                      : 'bg-[#f7f9fb] border-[#c0c8c2]'
                  }`}
                >
                  <div className="flex justify-between items-center mb-1">
                    <h4
                      className={`font-semibold text-[13.5px] ${
                        isDarkMode ? 'text-white' : 'text-[#191c1e]'
                      }`}
                    >
                      {role.title}
                    </h4>
                    <span
                      className={`text-[11px] font-mono-code px-2 py-0.5 rounded ${
                        isDarkMode ? 'bg-[#232c28] text-[#00ffcc]' : 'bg-[#e0e3e5] text-[#134231]'
                      }`}
                    >
                      {countForRole} {countForRole === 1 ? 'user' : 'users'}
                    </span>
                  </div>
                  <p className={`text-[11.5px] leading-relaxed ${isDarkMode ? 'text-[#b9cbc2]' : 'text-[#717974]'}`}>
                    {role.description}
                  </p>
                </div>
              );
            })}
          </div>

          <button
            onClick={() => setShowAddRoleModal(true)}
            className={`mt-4 w-full py-2 px-3 border border-dashed rounded-lg text-[13px] font-semibold flex items-center justify-center gap-1.5 transition-colors ${
              isDarkMode
                ? 'border-[#3a4a44] text-[#00ffcc] hover:bg-[#151d1a]'
                : 'border-[#c0c8c2] text-[#134231] hover:bg-[#f2f4f6]'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">add</span>
            Create Custom Role
          </button>
        </div>
      </div>

      {/* Add User Modal */}
      {showAddUserModal && (
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
              <div
                className="flex justify-between items-center mb-4 pb-3 border-b"
                style={{ borderColor: 'var(--color-border)' }}
              >
                <h3 className="type-title" style={{ color: 'var(--color-text-primary)' }}>
                  Add New Lab User
                </h3>
                <button
                  onClick={() => setShowAddUserModal(false)}
                  className="press-target p-1"
                  style={{ color: 'var(--color-text-tertiary)' }}
                >
                  <span className="material-symbols-outlined">close</span>
                </button>
              </div>

              <form onSubmit={handleCreateUser} className="space-y-3.5 text-[13px]">
                <div>
                  <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={newUserName}
                    onChange={(e) => setNewUserName(e.target.value)}
                    placeholder="e.g., Dr. Jane Austin"
                    className="w-full p-2 border focus:outline-none"
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
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={newUserEmail}
                    onChange={(e) => setNewUserEmail(e.target.value)}
                    placeholder="e.g., j.austin@dhatubodh.io"
                    className="w-full p-2 border focus:outline-none"
                    style={{
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--color-bg-base)',
                      borderColor: 'var(--color-border)',
                      color: 'var(--color-text-primary)',
                    }}
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                      Role
                    </label>
                    <select
                      value={newUserRole}
                      onChange={(e) => setNewUserRole(e.target.value as UserAccount['role'])}
                      className="w-full p-2 border focus:outline-none"
                      style={{
                        borderRadius: 'var(--radius-md)',
                        background: 'var(--color-bg-base)',
                        borderColor: 'var(--color-border)',
                        color: 'var(--color-text-primary)',
                      }}
                    >
                      <option value="Lab Tech">Lab Tech</option>
                      <option value="Snr. Metallurgist">Snr. Metallurgist</option>
                      <option value="Auditor">Auditor</option>
                      <option value="Service Acct">Service Acct</option>
                      <option value="SysAdmin">SysAdmin</option>
                    </select>
                  </div>

                  <div>
                    <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                      Department
                    </label>
                    <select
                      value={newUserDept}
                      onChange={(e) => setNewUserDept(e.target.value as UserAccount['department'])}
                      className="w-full p-2 border focus:outline-none"
                      style={{
                        borderRadius: 'var(--radius-md)',
                        background: 'var(--color-bg-base)',
                        borderColor: 'var(--color-border)',
                        color: 'var(--color-text-primary)',
                      }}
                    >
                      <option value="Operations">Operations</option>
                      <option value="Research">Research</option>
                      <option value="Quality Control">Quality Control</option>
                      <option value="Metallurgy">Metallurgy</option>
                      <option value="System">System</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                    Permissions Tier
                  </label>
                  <select
                    value={newUserPerm}
                    onChange={(e) => setNewUserPerm(e.target.value as UserAccount['permissions'])}
                    className="w-full p-2 border focus:outline-none"
                    style={{
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--color-bg-base)',
                      borderColor: 'var(--color-border)',
                      color: 'var(--color-text-primary)',
                    }}
                  >
                    <option value="Read-only">Read-only (Standard Access)</option>
                    <option value="Full Edit">Full Edit (Ratio Gates & Libraries)</option>
                    <option value="System Execution">System Execution (Automated API)</option>
                  </select>
                </div>

                <div className="flex justify-end gap-2 pt-3 border-t" style={{ borderColor: 'var(--color-border)' }}>
                  <button
                    type="button"
                    onClick={() => setShowAddUserModal(false)}
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
                    Create User
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Add Role Modal */}
      {showAddRoleModal && (
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
                  Create Custom Role
                </h3>
                <button
                  onClick={() => setShowAddRoleModal(false)}
                  className="press-target p-1"
                  style={{ color: 'var(--color-text-tertiary)' }}
                >
                  <span className="material-symbols-outlined">close</span>
                </button>
              </div>

              <form onSubmit={handleCreateRole} className="space-y-3.5 text-[13px]">
                <div>
                  <label className="type-caption block mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                    Role Title
                  </label>
                  <input
                    type="text"
                    value={newRoleTitle}
                    onChange={(e) => setNewRoleTitle(e.target.value)}
                    placeholder="e.g., Calibration Specialist"
                    className="w-full p-2 border focus:outline-none"
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
                    Role Scope & Description
                  </label>
                  <textarea
                    rows={3}
                    value={newRoleDesc}
                    onChange={(e) => setNewRoleDesc(e.target.value)}
                    placeholder="Describe permissions and department scopes..."
                    className="w-full p-2 border focus:outline-none"
                    style={{
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--color-bg-base)',
                      borderColor: 'var(--color-border)',
                      color: 'var(--color-text-primary)',
                    }}
                    required
                  />
                </div>

                <div className="flex justify-end gap-2 pt-3 border-t" style={{ borderColor: 'var(--color-border)' }}>
                  <button
                    type="button"
                    onClick={() => setShowAddRoleModal(false)}
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
                    Create Role
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
