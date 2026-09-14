import React from 'react';
import { NavSection, TopTab } from '../types';

interface NavigationProps {
  currentSection: NavSection;
  onNavigate: (section: NavSection) => void;
  topTab: TopTab;
  onSelectTopTab: (tab: TopTab) => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  onOpenNewAnalysis: () => void;
  onOpenExport: () => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}

export const Navigation: React.FC<NavigationProps> = ({
  currentSection,
  onNavigate,
  topTab,
  onSelectTopTab,
  isDarkMode,
  onToggleDarkMode,
  onOpenNewAnalysis,
  onOpenExport,
  searchQuery,
  onSearchChange,
}) => {
  return (
    <>
      {/* SideNavBar */}
      <aside
        id="side-navbar"
        className={`fixed left-0 top-0 h-full w-[280px] z-50 flex flex-col py-6 shadow-xl transition-colors duration-200 ${
          isDarkMode
            ? 'bg-[#1a2420] text-[#dbe5df] border-r border-[#3a4a44]'
            : 'bg-[#2c3c51] text-white'
        }`}
      >
        {/* Brand Header */}
        <div className="px-6 mb-8">
          <div className="flex items-center gap-3.5">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 transition-colors ${
                isDarkMode ? 'bg-[#00ffcc] text-[#00382b]' : 'bg-[#26fedc] text-[#007261]'
              }`}
            >
              <span className="material-symbols-outlined fill text-[22px]">science</span>
            </div>
            <div>
              <h1 className="font-display text-[20px] font-bold leading-tight text-white tracking-tight">
                MaterialID
              </h1>
              <p className={`text-[11px] font-semibold tracking-wider uppercase ${isDarkMode ? 'text-[#b9cbc2]' : 'text-[#b6c6e0]'}`}>
                Spectral Lab v2.4
              </p>
            </div>
          </div>

          {/* New Analysis CTA */}
          <button
            id="btn-sidebar-new-analysis"
            onClick={onOpenNewAnalysis}
            className={`mt-6 w-full py-2.5 px-4 rounded-lg font-medium text-[14px] shadow-sm flex items-center justify-center gap-2 transition-all active:scale-[0.98] ${
              isDarkMode
                ? 'bg-[#00ffcc] text-[#00382b] hover:bg-[#24ffcd] font-semibold'
                : 'bg-[#006b5b] hover:bg-[#134231] text-white'
            }`}
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            New Analysis
          </button>
        </div>

        {/* Primary Navigation Items */}
        <nav className="flex-1 px-3 space-y-1.5 overflow-y-auto">
          {/* Analyzer */}
          <button
            id="nav-item-analyzer"
            onClick={() => onNavigate('analyzer')}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-left transition-all ${
              currentSection === 'analyzer'
                ? isDarkMode
                  ? 'bg-[#414b47] text-[#00ffcc] font-semibold scale-[0.98]'
                  : 'bg-[#26fedc] text-[#007261] font-semibold scale-[0.98]'
                : isDarkMode
                ? 'text-[#b9cbc2] hover:bg-[#232c28] hover:text-white'
                : 'text-[#b6c6e0] hover:bg-[#435369] hover:text-white'
            }`}
          >
            <span
              className={`material-symbols-outlined text-[20px] ${
                currentSection === 'analyzer' ? 'fill' : ''
              }`}
            >
              science
            </span>
            <span className="text-[14px]">Analyzer</span>
          </button>

          {/* History */}
          <button
            id="nav-item-history"
            onClick={() => onNavigate('history')}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-left transition-all ${
              currentSection === 'history'
                ? isDarkMode
                  ? 'bg-[#414b47] text-[#00ffcc] font-semibold scale-[0.98]'
                  : 'bg-[#26fedc] text-[#007261] font-semibold scale-[0.98]'
                : isDarkMode
                ? 'text-[#b9cbc2] hover:bg-[#232c28] hover:text-white'
                : 'text-[#b6c6e0] hover:bg-[#435369] hover:text-white'
            }`}
          >
            <span
              className={`material-symbols-outlined text-[20px] ${
                currentSection === 'history' ? 'fill' : ''
              }`}
            >
              history
            </span>
            <span className="text-[14px]">History</span>
          </button>

          {/* Knowledge Base */}
          <button
            id="nav-item-knowledge"
            onClick={() => onNavigate('knowledge')}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-left transition-all ${
              currentSection === 'knowledge' || currentSection === 'gate-editor'
                ? isDarkMode
                  ? 'bg-[#414b47] text-[#00ffcc] font-semibold scale-[0.98]'
                  : 'bg-[#26fedc] text-[#007261] font-semibold scale-[0.98]'
                : isDarkMode
                ? 'text-[#b9cbc2] hover:bg-[#232c28] hover:text-white'
                : 'text-[#b6c6e0] hover:bg-[#435369] hover:text-white'
            }`}
          >
            <span
              className={`material-symbols-outlined text-[20px] ${
                currentSection === 'knowledge' || currentSection === 'gate-editor' ? 'fill' : ''
              }`}
            >
              menu_book
            </span>
            <span className="text-[14px]">Knowledge Base</span>
          </button>

          {/* Settings */}
          <button
            id="nav-item-settings"
            onClick={() => onNavigate('settings')}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-left transition-all ${
              currentSection === 'settings'
                ? isDarkMode
                  ? 'bg-[#414b47] text-[#00ffcc] font-semibold scale-[0.98]'
                  : 'bg-[#26fedc] text-[#007261] font-semibold scale-[0.98]'
                : isDarkMode
                ? 'text-[#b9cbc2] hover:bg-[#232c28] hover:text-white'
                : 'text-[#b6c6e0] hover:bg-[#435369] hover:text-white'
            }`}
          >
            <span
              className={`material-symbols-outlined text-[20px] ${
                currentSection === 'settings' ? 'fill' : ''
              }`}
            >
              settings
            </span>
            <span className="text-[14px]">Settings</span>
          </button>
        </nav>

        {/* Footer info & user stub */}
        <div
          className={`mt-auto px-4 pt-4 mx-3 border-t ${
            isDarkMode ? 'border-[#2e3733]' : 'border-[#435369]'
          }`}
        >
          <div className="space-y-1 mb-4">
            <div
              className={`flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[11px] font-bold uppercase tracking-wider cursor-pointer transition-colors ${
                isDarkMode
                  ? 'text-[#b9cbc2] hover:text-white hover:bg-[#232c28]'
                  : 'text-[#b6c6e0] hover:text-white hover:bg-[#435369]'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="material-symbols-outlined text-[16px]">check_circle</span>
              <span>System Status: Online</span>
            </div>
            <a
              href="#docs"
              onClick={(e) => {
                e.preventDefault();
                alert('Spectral Lab documentation & ASTM standards reference library loaded.');
              }}
              className={`flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[11px] font-bold uppercase tracking-wider transition-colors ${
                isDarkMode
                  ? 'text-[#b9cbc2] hover:text-white hover:bg-[#232c28]'
                  : 'text-[#b6c6e0] hover:text-white hover:bg-[#435369]'
              }`}
            >
              <span className="material-symbols-outlined text-[16px]">help</span>
              <span>Documentation</span>
            </a>
          </div>

          {/* User Profile avatar */}
          <div
            onClick={() => onNavigate('settings')}
            className={`flex items-center gap-2.5 p-1.5 rounded-lg cursor-pointer transition-colors ${
              isDarkMode ? 'hover:bg-[#232c28]' : 'hover:bg-[#435369]'
            }`}
            title="Logged in as Admin User (SysAdmin)"
          >
            <div className="w-8 h-8 rounded-full flex items-center justify-center bg-emerald-500/20 text-emerald-400 font-bold text-[12px] border border-emerald-400 shrink-0">
              <span className="material-symbols-outlined text-[18px]">person</span>
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[13px] font-medium text-white truncate">Admin User</p>
              <p
                className={`text-[10px] uppercase font-bold tracking-wider truncate ${
                  isDarkMode ? 'text-[#00ffcc]' : 'text-[#26fedc]'
                }`}
              >
                SysAdmin
              </p>
            </div>
          </div>
        </div>
      </aside>

      {/* TopNavBar */}
      <header
        id="top-navbar"
        className={`fixed top-0 left-[280px] right-0 h-16 px-6 z-40 flex items-center justify-between border-b transition-colors duration-200 ${
          isDarkMode
            ? 'bg-[#0c1512] border-[#3a4a44] text-[#dbe5df]'
            : 'bg-[#f7f9fb] border-[#c0c8c2] text-[#191c1e]'
        }`}
      >
        {/* Left: Title or Back breadcrumb */}
        <div className="flex items-center gap-6 h-full">
          {currentSection === 'gate-editor' ? (
            <button
              id="btn-back-to-knowledge"
              onClick={() => onNavigate('knowledge')}
              className={`flex items-center gap-1.5 font-semibold text-[14px] transition-colors ${
                isDarkMode ? 'text-[#00ffcc] hover:underline' : 'text-[#134231] hover:text-[#006b5b]'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">arrow_back</span>
              <span>Back</span>
              <span className="opacity-40 ml-1">/</span>
              <span className="ml-1 text-[13px] opacity-75">Particle Identification System</span>
            </button>
          ) : (
            <span
              className={`font-semibold text-[15px] tracking-tight ${
                isDarkMode ? 'text-white' : 'text-[#134231]'
              }`}
            >
              Particle Identification System
            </span>
          )}

          {/* Sub Navigation Links */}
          <div className="hidden md:flex h-full items-center gap-4 ml-4">
            <button
              id="top-tab-dashboard"
              onClick={() => {
                onSelectTopTab('dashboard');
                onNavigate('analyzer');
              }}
              className={`h-full flex items-center px-2 text-[14px] transition-all border-b-2 ${
                topTab === 'dashboard' && currentSection === 'analyzer'
                  ? isDarkMode
                    ? 'border-[#00ffcc] text-[#00ffcc] font-bold'
                    : 'border-[#134231] text-[#134231] font-bold'
                  : 'border-transparent text-[#717974] hover:text-[#191c1e] dark:hover:text-white'
              }`}
            >
              Dashboard
            </button>
            <button
              id="top-tab-reports"
              onClick={() => {
                onSelectTopTab('reports');
                onOpenExport();
              }}
              className={`h-full flex items-center px-2 text-[14px] transition-all border-b-2 ${
                topTab === 'reports'
                  ? isDarkMode
                    ? 'border-[#00ffcc] text-[#00ffcc] font-bold'
                    : 'border-[#134231] text-[#134231] font-bold'
                  : 'border-transparent text-[#717974] hover:text-[#191c1e] dark:hover:text-white'
              }`}
            >
              Reports
            </button>
            <button
              id="top-tab-archive"
              onClick={() => {
                onSelectTopTab('archive');
                onNavigate('history');
              }}
              className={`h-full flex items-center px-2 text-[14px] transition-all border-b-2 ${
                topTab === 'archive' || currentSection === 'history'
                  ? isDarkMode
                    ? 'border-[#00ffcc] text-[#00ffcc] font-bold'
                    : 'border-[#134231] text-[#134231] font-bold'
                  : 'border-transparent text-[#717974] hover:text-[#191c1e] dark:hover:text-white'
              }`}
            >
              Archive
            </button>
          </div>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          {/* Search Box */}
          <div className="relative">
            <span
              className={`material-symbols-outlined absolute left-2.5 top-1/2 -translate-y-1/2 text-[18px] ${
                isDarkMode ? 'text-[#83958d]' : 'text-[#717974]'
              }`}
            >
              search
            </span>
            <input
              id="global-search-input"
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search data, grades, components..."
              className={`pl-8 pr-4 py-1.5 text-[13px] rounded-full border transition-all w-56 focus:w-64 focus:outline-none ${
                isDarkMode
                  ? 'bg-[#151d1a] border-[#3a4a44] text-[#dbe5df] focus:border-[#00ffcc] focus:ring-1 focus:ring-[#00ffcc]'
                  : 'bg-[#f2f4f6] border-[#c0c8c2] text-[#191c1e] focus:border-[#134231] focus:ring-1 focus:ring-[#134231]'
              }`}
            />
          </div>

          {/* Theme Toggle Button */}
          <button
            id="btn-toggle-theme"
            onClick={onToggleDarkMode}
            title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
              isDarkMode
                ? 'text-[#00ffcc] hover:bg-[#232c28]'
                : 'text-[#2c3c51] hover:bg-[#e0e3e5]'
            }`}
          >
            <span className="material-symbols-outlined text-[19px]">
              {isDarkMode ? 'light_mode' : 'dark_mode'}
            </span>
          </button>

          {/* Support */}
          <button
            id="btn-support"
            onClick={() => alert('Support Helpdesk: Particle Identification System v2.4 (Spectral Lab).\nDirect line: ext-4029 (Metallurgy Lab).')}
            className={`text-[11px] font-bold tracking-wider uppercase px-2.5 py-1 rounded-full transition-colors ${
              isDarkMode
                ? 'text-[#b9cbc2] hover:bg-[#232c28] hover:text-white'
                : 'text-[#414944] hover:bg-[#eceef0] hover:text-[#191c1e]'
            }`}
          >
            Support
          </button>

          {/* Export Data */}
          <button
            id="btn-topbar-export"
            onClick={onOpenExport}
            className={`text-[11px] font-bold tracking-wider uppercase px-3.5 py-1.5 rounded-full transition-all shadow-sm ${
              isDarkMode
                ? 'bg-[#00ffcc] text-[#00382b] hover:bg-[#24ffcd]'
                : 'bg-[#134231] text-white hover:bg-[#2d5a47]'
            }`}
          >
            Export Data
          </button>

          <div
            className={`h-6 w-px mx-1 ${
              isDarkMode ? 'bg-[#3a4a44]' : 'bg-[#c0c8c2]'
            }`}
          />

          {/* Notifications */}
          <button
            id="btn-notifications"
            onClick={() => alert('3 Notifications:\n• Calibration passed at 09:15:00\n• 1 new particle scan added\n• 12 changes in last 30 days')}
            className={`relative w-8 h-8 flex items-center justify-center rounded-full transition-colors ${
              isDarkMode
                ? 'text-[#b9cbc2] hover:bg-[#232c28] hover:text-white'
                : 'text-[#414944] hover:bg-[#eceef0] hover:text-[#191c1e]'
            }`}
          >
            <span className="material-symbols-outlined text-[20px]">notifications</span>
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-emerald-500"></span>
          </button>

          {/* Top user avatar */}
          <button
            id="btn-topbar-avatar"
            onClick={() => onNavigate('settings')}
            className="w-8 h-8 rounded-full flex items-center justify-center bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 hover:ring-2 hover:ring-emerald-400 transition-all shrink-0"
            title="User Settings & Role Management"
          >
            <span className="material-symbols-outlined text-[20px]">account_circle</span>
          </button>
        </div>
      </header>
    </>
  );
};
