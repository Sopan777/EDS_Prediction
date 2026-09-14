import { useState, useEffect } from 'react';
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
import {
  INITIAL_MATERIAL_FAMILIES,
  INITIAL_USERS,
  ROLE_DEFINITIONS,
  INITIAL_AUDIT_LOGS,
} from './data/mockData';
import { Navigation } from './components/Navigation';
import { AnalyzerView } from './components/AnalyzerView';
import { KnowledgeBaseView } from './components/KnowledgeBaseView';
import { RatioGateEditorView } from './components/RatioGateEditorView';
import { AuditLogView } from './components/AuditLogView';
import { UserManagementView } from './components/UserManagementView';
import { ComponentModal } from './components/ComponentModal';
import { ExportModal } from './components/ExportModal';
import { NewAnalysisModal } from './components/NewAnalysisModal';

export function App() {
  // Theme state (default to dark mode as highlighted in spectral lab screenshots, with instant light toggle)
  const [isDarkMode, setIsDarkMode] = useState<boolean>(() => {
    return localStorage.getItem('spectral_theme') !== 'light';
  });

  // Navigation state
  const [currentSection, setCurrentSection] = useState<NavSection>('analyzer');
  const [topTab, setTopTab] = useState<TopTab>('dashboard');
  const [globalSearch, setGlobalSearch] = useState('');

  // Application Data States
  const [materialFamilies, setMaterialFamilies] = useState<MaterialFamily[]>(INITIAL_MATERIAL_FAMILIES);
  const [activeFamily, setActiveFamily] = useState<MaterialFamily>(INITIAL_MATERIAL_FAMILIES[0]);
  const [users, setUsers] = useState<UserAccount[]>(INITIAL_USERS);
  const [roles, setRoles] = useState<RoleDefinition[]>(ROLE_DEFINITIONS);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>(INITIAL_AUDIT_LOGS);

  // Modal States
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

  // Fetch live application data from Python backend API
  useEffect(() => {
    fetch('/api/families')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && Array.isArray(data) && data.length > 0) {
          setMaterialFamilies(data);
          setActiveFamily((prev) => {
            const found = data.find((f: MaterialFamily) => f.code === prev.code);
            return found || data[0];
          });
        }
      })
      .catch((e) => console.warn('Using baseline families:', e));

    fetch('/api/users')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && Array.isArray(data) && data.length > 0) {
          setUsers(data);
        }
      })
      .catch((e) => console.warn('Using baseline users:', e));

    fetch('/api/audit-logs')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && Array.isArray(data) && data.length > 0) {
          setAuditLogs(data);
        }
      })
      .catch((e) => console.warn('Using baseline audit logs:', e));
  }, []);

  const handleToggleTheme = () => {
    setIsDarkMode((prev) => !prev);
  };

  // Ratio gates save handler
  const handleSaveGates = (familyId: string, updatedGates: RatioGate[]) => {
    setMaterialFamilies((prev) =>
      prev.map((fam) => {
        if (fam.id === familyId) {
          return { ...fam, ratioGates: updatedGates };
        }
        return fam;
      })
    );

    setActiveFamily((prev) => ({
      ...prev,
      ratioGates: updatedGates,
    }));

    // Add entry to audit log
    const currentUser = users[0]?.name || 'Dr. Marcus Vance';
    const currentRole = users[0]?.role || 'Snr. Metallurgist';
    const newLog: AuditLogEntry = {
      id: `audit-${Date.now()}`,
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19),
      user: currentUser,
      userRole: currentRole,
      action: `Updated Ratio Gates configuration for ${activeFamily?.code || 'Family'}`,
      actionType: 'Gate Edit',
      familyCode: activeFamily?.code || 'F4',
      changeDetails: {
        from: `${activeFamily?.ratioGates?.length || 0} active gates`,
        to: `${updatedGates.filter((g) => g.enabled).length} active gates`,
      },
      impactText: 'Gates re-calibrated and saved to knowledge base',
      impactType: 'positive',
    };

    setAuditLogs((prev) => [newLog, ...prev]);

    // Persist to backend API
    fetch(`/api/gates/${activeFamily.code}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gates: updatedGates }),
    }).catch((err) => console.error('Failed to persist ratio gates:', err));

    fetch('/api/audit-logs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newLog),
    }).catch((err) => console.error('Failed to log gate edit audit:', err));

    setCurrentSection('knowledge');
  };

  // User management handlers
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

  const handleStartSession = () => {
    setCurrentSection('analyzer');
    setTopTab('dashboard');
  };

  return (
    <div
      className={`min-h-screen flex transition-colors duration-200 ${
        isDarkMode ? 'bg-[#0c1512] text-[#dbe5df]' : 'bg-[#f7f9fb] text-[#191c1e]'
      }`}
    >
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
        className="ml-[280px] mt-16 flex-1 p-6 overflow-hidden h-[calc(100vh-64px)]"
      >
        {currentSection === 'analyzer' && (
          <AnalyzerView
            isDarkMode={isDarkMode}
            activeFamily={activeFamily}
            onSelectFamily={setActiveFamily}
            onSelectComponent={(comp) => setSelectedComponent(comp)}
            allFamilies={materialFamilies}
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

        {currentSection === 'gate-editor' && (
          <RatioGateEditorView
            isDarkMode={isDarkMode}
            activeFamily={activeFamily}
            onSaveGates={handleSaveGates}
            onBack={() => setCurrentSection('knowledge')}
          />
        )}

        {currentSection === 'history' && (
          <AuditLogView isDarkMode={isDarkMode} auditLogs={auditLogs} />
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
