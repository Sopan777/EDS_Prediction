import { useState, useEffect, useCallback } from 'react';
import {
  NavSection,
  TopTab,
  MaterialFamily,
  CandidateComponent,
  RatioGate,
  UserAccount,
  RoleDefinition,
  AuditLogEntry,
} from './types';
import { ROLE_DEFINITIONS } from './data/mockData';
import { Navigation } from './components/Navigation';
import { AnalyzerView } from './components/AnalyzerView';
import { KnowledgeBaseView } from './components/KnowledgeBaseView';
import { RatioGateEditorView } from './components/RatioGateEditorView';
import { AuditLogView } from './components/AuditLogView';
import { UserManagementView } from './components/UserManagementView';
import { AnalysisHistoryView } from './components/AnalysisHistoryView';
import { ComponentModal } from './components/ComponentModal';
import { ExportModal } from './components/ExportModal';
import { NewAnalysisModal } from './components/NewAnalysisModal';

// --------------------------------------------------------------------------
// Loading / Error banner helpers
// --------------------------------------------------------------------------

function BackendErrorBanner() {
  return (
    <div
      className="fixed top-0 left-0 right-0 z-[999] px-4 py-2 flex items-center gap-2 text-[13px] font-semibold anim-slide-down"
      style={{
        background: 'var(--color-fail-subtle)',
        color: 'var(--color-fail)',
        borderBottom: '1px solid var(--color-fail)',
      }}
    >
      <span className="material-symbols-outlined text-[18px]">warning</span>
      Backend unreachable — check that the Python server is running on port 5000.
      No analysis data is available.
    </div>
  );
}

function LoadingSpinner() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <div
        className="w-10 h-10 rounded-full border-4 border-t-transparent animate-spin"
        style={{ borderColor: 'var(--color-border-strong)', borderTopColor: 'var(--color-accent)' }}
      />
      <p className="type-subhead" style={{ color: 'var(--color-text-tertiary)' }}>
        Connecting to Dhatu Bodh server…
      </p>
    </div>
  );
}

// --------------------------------------------------------------------------
// App component
// --------------------------------------------------------------------------

export function App() {
  // Theme
  const [isDarkMode, setIsDarkMode] = useState<boolean>(() => {
    return localStorage.getItem('spectral_theme') !== 'light';
  });

  // Navigation
  const [currentSection, setCurrentSection] = useState<NavSection>('analyzer');
  const [topTab, setTopTab] = useState<TopTab>('dashboard');
  const [globalSearch, setGlobalSearch] = useState('');

  // --------------------------------------------------------------------------
  // Application Data States — NO mock data initial values
  // --------------------------------------------------------------------------
  const [materialFamilies, setMaterialFamilies] = useState<MaterialFamily[]>([]);
  const [activeFamily, setActiveFamily] = useState<MaterialFamily | null>(null);
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [roles, setRoles] = useState<RoleDefinition[]>(ROLE_DEFINITIONS);   // Static config, not backend data
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);

  // Loading / error states
  const [familiesLoading, setFamiliesLoading] = useState(true);
  const [usersLoading, setUsersLoading] = useState(true);
  const [logsLoading, setLogsLoading] = useState(true);
  const [backendError, setBackendError] = useState(false);

  // Modal states
  const [selectedComponent, setSelectedComponent] = useState<CandidateComponent | null>(null);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isNewAnalysisOpen, setIsNewAnalysisOpen] = useState(false);

  // Synchronize HTML dark class
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('spectral_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('spectral_theme', 'light');
    }
  }, [isDarkMode]);

  // --------------------------------------------------------------------------
  // Backend data loaders
  // --------------------------------------------------------------------------

  const loadFamilies = useCallback(() => {
    setFamiliesLoading(true);
    fetch('/api/families')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: MaterialFamily[]) => {
        if (Array.isArray(data)) {
          setMaterialFamilies(data);
          setActiveFamily((prev) => {
            if (prev) {
              const found = data.find((f) => f.code === prev.code);
              return found || data[0] || null;
            }
            return data[0] || null;
          });
          setBackendError(false);
        }
      })
      .catch(() => setBackendError(true))
      .finally(() => setFamiliesLoading(false));
  }, []);

  const loadUsers = useCallback(() => {
    setUsersLoading(true);
    fetch('/api/users')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: UserAccount[]) => {
        if (Array.isArray(data)) setUsers(data);
      })
      .catch(() => {}) // Users are non-critical; don't show global error
      .finally(() => setUsersLoading(false));
  }, []);

  const loadAuditLogs = useCallback(() => {
    setLogsLoading(true);
    fetch('/api/audit-logs')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: AuditLogEntry[]) => {
        if (Array.isArray(data)) setAuditLogs(data);
      })
      .catch(() => {})
      .finally(() => setLogsLoading(false));
  }, []);

  // Initial data load on mount
  useEffect(() => {
    loadFamilies();
    loadUsers();
    loadAuditLogs();
  }, [loadFamilies, loadUsers, loadAuditLogs]);

  const handleToggleTheme = () => setIsDarkMode((prev) => !prev);

  // --------------------------------------------------------------------------
  // Ratio gates save handler
  // --------------------------------------------------------------------------
  const handleSaveGates = (familyId: string, updatedGates: RatioGate[]) => {
    // Update local state
    setMaterialFamilies((prev) =>
      prev.map((fam) =>
        fam.code === familyId ? { ...fam, ratioGates: updatedGates } : fam
      )
    );
    setActiveFamily((prev) =>
      prev ? { ...prev, ratioGates: updatedGates } : prev
    );

    // Persist gates to backend (include user from state if available)
    const actingUser = users[0]?.name || 'Lab Operator';
    const actingRole = users[0]?.role || 'Metallurgist';

    fetch(`/api/gates/${familyId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        gates: updatedGates,
        user: actingUser,
        userRole: actingRole,
      }),
    })
      .then((r) => r.ok && r.json())
      .then(() => {
        // Refresh audit logs from backend after gate save
        loadAuditLogs();
        // Refresh families (gates may have changed displayed ratioGates)
        loadFamilies();
      })
      .catch((err) => console.error('Failed to persist ratio gates:', err));

    setCurrentSection('knowledge');
  };

  // --------------------------------------------------------------------------
  // User management handlers
  // --------------------------------------------------------------------------
  const handleAddUser = (newUser: UserAccount) => {
    setUsers((prev) => [newUser, ...prev]);
    fetch('/api/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newUser),
    }).catch((err) => console.error('Failed to persist user:', err));
  };

  const handleUpdateUser = (userId: string, updates: Partial<UserAccount>) => {
    setUsers((prev) =>
      prev.map((u) => (u.id === userId ? { ...u, ...updates } : u))
    );
    fetch(`/api/users/${userId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    }).catch((err) => console.error('Failed to update user:', err));
  };

  const handleAddRole = (newRole: RoleDefinition) => {
    setRoles((prev) => [...prev, newRole]);
  };

  // --------------------------------------------------------------------------
  // New analysis session — persist to backend
  // --------------------------------------------------------------------------
  const handleStartSession = (info: {
    particleId: string;
    spectrometer: string;
    description: string;
  }) => {
    // Save session to backend for tracking
    fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        particleId: info.particleId,
        spectrometer: info.spectrometer,
        description: info.description,
        createdBy: users[0]?.name || 'Lab Operator',
      }),
    }).catch((err) => console.warn('Session not saved:', err));

    setCurrentSection('analyzer');
    setTopTab('dashboard');
  };

  const isInitialLoading = familiesLoading && materialFamilies.length === 0;

  return (
    <div
      className="min-h-screen flex"
      style={{
        background: 'var(--color-bg-base)',
        color: 'var(--color-text-primary)',
        transition: 'background var(--dur-normal), color var(--dur-normal)',
      }}
    >
      {/* Backend error banner */}
      {backendError && <BackendErrorBanner />}

      {/* Side & Top Navigation */}
      <Navigation
        currentSection={currentSection}
        onNavigate={(section) => {
          setCurrentSection(section);
          if (section === 'analyzer') setTopTab('dashboard');
          if (section === 'history') setTopTab('archive');
        }}
        topTab={topTab}
        onSelectTopTab={(tab) => {
          setTopTab(tab);
          if (tab === 'dashboard') setCurrentSection('analyzer');
          if (tab === 'archive') setCurrentSection('history');
          if (tab === 'reports') setIsExportOpen(true);
        }}
        isDarkMode={isDarkMode}
        onToggleDarkMode={handleToggleTheme}
        onOpenNewAnalysis={() => setIsNewAnalysisOpen(true)}
        onOpenExport={() => setIsExportOpen(true)}
        searchQuery={globalSearch}
        onSearchChange={setGlobalSearch}
      />

      {/* Main View Container */}
      <main
        id="main-content-viewport"
        className={`ml-[280px] flex-1 p-6 overflow-hidden h-[calc(100vh-64px)] ${
          backendError ? 'mt-[76px]' : 'mt-16'
        }`}
      >
        {/* Global loading state */}
        {isInitialLoading ? (
          <LoadingSpinner />
        ) : (
          <>
            {currentSection === 'analyzer' && (
              <AnalyzerView
                isDarkMode={isDarkMode}
                activeFamily={activeFamily}
                onSelectFamily={setActiveFamily}
                onSelectComponent={(comp) => setSelectedComponent(comp)}
                allFamilies={materialFamilies}
                onAnalysisComplete={() => loadAuditLogs()}
              />
            )}

            {currentSection === 'knowledge' && (
              <KnowledgeBaseView
                isDarkMode={isDarkMode}
                activeFamily={activeFamily}
                onSelectFamily={setActiveFamily}
                onOpenGateEditor={() => setCurrentSection('gate-editor')}
                onSelectComponent={(comp) => setSelectedComponent(comp)}
                families={materialFamilies}
              />
            )}

            {currentSection === 'gate-editor' && activeFamily && (
              <RatioGateEditorView
                isDarkMode={isDarkMode}
                activeFamily={activeFamily}
                onSaveGates={handleSaveGates}
                onBack={() => setCurrentSection('knowledge')}
              />
            )}

            {currentSection === 'history' && (
              <AnalysisHistoryView
                isDarkMode={isDarkMode}
              />
            )}

            {currentSection === 'settings' && (
              <UserManagementView
                isDarkMode={isDarkMode}
                users={users}
                roles={roles}
                onAddUser={handleAddUser}
                onUpdateUser={handleUpdateUser}
                onAddRole={handleAddRole}
              />
            )}
          </>
        )}
      </main>

      {/* Candidate Component Spec Modal */}
      <ComponentModal
        component={selectedComponent}
        onClose={() => setSelectedComponent(null)}
        isDarkMode={isDarkMode}
      />

      {/* Laboratory Export Modal */}
      <ExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        isDarkMode={isDarkMode}
        activeFamily={activeFamily}
      />

      {/* New Analysis / Spectrometer Scan Loader Modal */}
      <NewAnalysisModal
        isOpen={isNewAnalysisOpen}
        onClose={() => setIsNewAnalysisOpen(false)}
        isDarkMode={isDarkMode}
        onStartSession={handleStartSession}
      />
    </div>
  );
}

export default App;
