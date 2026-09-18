import React, { useState } from 'react';
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

interface NavItemProps {
  id: string;
  label: string;
  icon: string;
  active: boolean;
  onClick: () => void;
}

const NavItem: React.FC<NavItemProps> = ({ id, label, icon, active, onClick }) => (
  <button
    id={id}
    onClick={onClick}
    aria-current={active ? 'page' : undefined}
    className="w-full flex items-center gap-3 px-3 py-2.5 text-left press-target relative transition-colors hover:bg-white/5"
    style={{
      borderRadius: 'var(--radius-md)',
      background: active ? 'rgba(255,255,255,0.07)' : undefined,
    }}
  >
    {active && (
      <span
        className="absolute left-0 top-2 bottom-2 w-[3px] rounded-full"
        style={{ background: 'var(--color-accent)' }}
      />
    )}
    <span
      className={`material-symbols-outlined text-[20px] ml-1 ${active ? 'fill' : ''}`}
      style={{ color: active ? 'var(--color-accent)' : 'var(--color-text-on-sidebar-muted)' }}
    >
      {icon}
    </span>
    <span
      className="type-subhead"
      style={{
        fontWeight: active ? 600 : 400,
        color: active ? 'var(--color-text-on-sidebar)' : 'var(--color-text-on-sidebar-muted)',
      }}
    >
      {label}
    </span>
  </button>
);

interface TopTabButtonProps {
  id: string;
  label: string;
  active: boolean;
  onClick: () => void;
}

const TopTabButton: React.FC<TopTabButtonProps> = ({ id, label, active, onClick }) => (
  <button
    id={id}
    onClick={onClick}
    className="h-full flex items-center px-1 text-[14px] border-b-2 press-target transition-all"
    style={{
      fontWeight: active ? 600 : 400,
      borderColor: active ? 'var(--color-accent)' : 'transparent',
      color: active ? 'var(--color-accent)' : 'var(--color-text-tertiary)',
    }}
  >
    {label}
  </button>
);

const NOTIFICATIONS = [
  { id: 'n1', icon: 'check_circle', text: 'Calibration passed', time: '09:15', type: 'pass' },
  { id: 'n2', icon: 'science',       text: '1 new particle scan added', time: '08:42', type: 'info' },
  { id: 'n3', icon: 'edit_note',     text: '12 gate changes in last 30 days', time: '2d ago', type: 'warn' },
];

const NotificationsDropdown: React.FC<{ onClose: () => void }> = ({ onClose }) => (
  <div
    className="absolute right-0 top-full mt-2 w-72 rounded-[var(--radius-lg)] border anim-slide-down z-50 overflow-hidden"
    style={{
      background: 'var(--color-bg-card)',
      borderColor: 'var(--color-border)',
      boxShadow: 'var(--shadow-modal)',
    }}
  >
    <div className="px-4 py-3 border-b flex items-center justify-between" style={{ borderColor: 'var(--color-border)' }}>
      <span className="type-subhead font-semibold" style={{ color: 'var(--color-text-primary)' }}>
        Notifications
      </span>
      <button onClick={onClose} className="press-target" style={{ color: 'var(--color-text-tertiary)' }}>
        <span className="material-symbols-outlined text-[18px]">close</span>
      </button>
    </div>
    {NOTIFICATIONS.map((n) => (
      <div
        key={n.id}
        className="flex items-start gap-3 px-4 py-3 border-b last:border-b-0 transition-colors"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <span
          className="material-symbols-outlined text-[18px] mt-0.5 shrink-0"
          style={{ color: n.type === 'pass' ? 'var(--color-pass)' : n.type === 'warn' ? 'var(--color-warn)' : 'var(--color-accent)' }}
        >
          {n.icon}
        </span>
        <div className="flex-1 min-w-0">
          <p className="type-subhead" style={{ color: 'var(--color-text-primary)' }}>{n.text}</p>
          <p className="type-caption mt-0.5" style={{ color: 'var(--color-text-tertiary)' }}>{n.time}</p>
        </div>
      </div>
    ))}
  </div>
);

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
  const [showNotifications, setShowNotifications] = useState(false);

  const navItems = [
    { id: 'nav-item-analyzer',  label: 'Analyzer',       icon: 'science',   section: 'analyzer'  as NavSection },
    { id: 'nav-item-history',   label: 'History',        icon: 'history',   section: 'history'   as NavSection },
    { id: 'nav-item-knowledge', label: 'Knowledge Base', icon: 'menu_book', section: 'knowledge' as NavSection },
    { id: 'nav-item-settings',  label: 'Settings',       icon: 'settings',  section: 'settings'  as NavSection },
  ];

  return (
    <>
      {/* ── Sidebar ────────────────────────────────────────────── */}
      <aside
        id="side-navbar"
        className="fixed left-0 top-0 h-full w-[280px] z-50 flex flex-col py-6"
        style={{ background: 'var(--color-bg-sidebar)', boxShadow: 'var(--shadow-sidebar)' }}
      >
        {/* Brand */}
        <div className="px-5 mb-8">
          <div className="flex items-center gap-3">
            {/* Dhatu Bodh logo mark — white pill so the blue logo reads on dark sidebar */}
            <div
              className="shrink-0 flex items-center justify-center overflow-hidden"
              style={{
                width: '40px',
                height: '40px',
                borderRadius: 'var(--radius-md)',
                background: '#ffffff',
                padding: '3px',
              }}
            >
              <img
                src="/dhatu_bodh_logo.jpg"
                alt="Dhatu Bodh logo"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            </div>
            <div>
              <h1
                className="font-display font-bold"
                style={{ fontSize: '17px', color: 'var(--color-text-on-sidebar)', letterSpacing: '-0.01em', lineHeight: 1.2 }}
              >
                Dhatu Bodh
              </h1>
              <p className="type-caption" style={{ color: 'var(--color-text-on-sidebar-muted)' }}>
                Spectral Lab v2.4
              </p>
            </div>
          </div>


          <button
            id="btn-sidebar-new-analysis"
            onClick={onOpenNewAnalysis}
            className="press-target mt-5 w-full py-2.5 px-4 type-subhead font-semibold flex items-center justify-center gap-2"
            style={{ background: 'var(--color-accent)', color: 'var(--color-accent-on)', borderRadius: 'var(--radius-md)' }}
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            New Analysis
          </button>
        </div>

        {/* Nav items */}
        <nav className="flex-1 px-3 space-y-1 overflow-y-auto" aria-label="Main navigation">
          {navItems.map((item) => (
            <NavItem
              key={item.id}
              id={item.id}
              label={item.label}
              icon={item.icon}
              active={currentSection === item.section || (item.section === 'knowledge' && currentSection === 'gate-editor')}
              onClick={() => onNavigate(item.section)}
            />
          ))}
        </nav>

        {/* Footer */}
        <div className="mt-auto px-4 pt-4 mx-3 border-t" style={{ borderColor: 'rgba(255,255,255,0.10)' }}>
          <div className="flex items-center gap-2 px-2 py-1.5 mb-1">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ background: 'var(--color-pass)' }} />
            <span className="type-caption" style={{ color: 'var(--color-text-on-sidebar-muted)' }}>System Online</span>
          </div>

          <a
            href="/docs"
            className="press-target flex items-center gap-2 px-2 py-1.5 mb-3 transition-colors hover:bg-white/5"
            style={{ color: 'var(--color-text-on-sidebar-muted)', textDecoration: 'none', borderRadius: 'var(--radius-sm)' }}
          >
            <span className="material-symbols-outlined text-[16px]">help_outline</span>
            <span className="type-caption">Documentation</span>
          </a>

          <button
            onClick={() => onNavigate('settings')}
            className="press-target w-full flex items-center gap-2.5 p-2 transition-colors hover:bg-white/5"
            style={{ borderRadius: 'var(--radius-md)' }}
            title="User Settings"
          >
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 border"
              style={{ background: 'var(--color-accent-subtle)', borderColor: 'var(--color-accent)', color: 'var(--color-accent)' }}
            >
              <span className="material-symbols-outlined text-[18px]">person</span>
            </div>
            <div className="min-w-0 flex-1 text-left">
              <p className="type-subhead font-medium truncate" style={{ color: 'var(--color-text-on-sidebar)' }}>Admin User</p>
              <p className="type-caption truncate" style={{ color: 'var(--color-accent)' }}>SysAdmin</p>
            </div>
          </button>
        </div>
      </aside>

      {/* ── Top Bar ─────────────────────────────────────────────── */}
      <header
        id="top-navbar"
        className="material-thin fixed top-0 left-[280px] right-0 h-16 px-6 z-40 flex items-center justify-between border-b"
        style={{ borderColor: 'var(--color-border)' }}
      >
        {/* Left */}
        <div className="flex items-center gap-4 h-full">
          {currentSection === 'gate-editor' ? (
            <button
              id="btn-back-to-knowledge"
              onClick={() => onNavigate('knowledge')}
              className="press-target flex items-center gap-1.5 type-subhead font-semibold"
              style={{ color: 'var(--color-accent)' }}
            >
              <span className="material-symbols-outlined text-[18px]">arrow_back</span>
              Back
              <span className="mx-1.5 opacity-30">/</span>
              <span className="opacity-60 font-normal">Dhatu Bodh</span>
            </button>
          ) : (
            <span className="type-headline" style={{ color: 'var(--color-text-primary)' }}>
              Particle Identification System
            </span>
          )}

          <div className="hidden md:flex h-full items-center gap-2 ml-2">
            <TopTabButton id="top-tab-dashboard" label="Dashboard"
              active={topTab === 'dashboard' && currentSection === 'analyzer'}
              onClick={() => { onSelectTopTab('dashboard'); onNavigate('analyzer'); }} />
            <TopTabButton id="top-tab-reports" label="Reports"
              active={topTab === 'reports'}
              onClick={() => { onSelectTopTab('reports'); onOpenExport(); }} />
            <TopTabButton id="top-tab-archive" label="Archive"
              active={topTab === 'archive' || currentSection === 'history'}
              onClick={() => { onSelectTopTab('archive'); onNavigate('history'); }} />
          </div>
        </div>

        {/* Right */}
        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative">
            <span className="material-symbols-outlined absolute left-2.5 top-1/2 -translate-y-1/2 text-[18px] pointer-events-none" style={{ color: 'var(--color-text-tertiary)' }}>
              search
            </span>
            <input
              id="global-search-input"
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search grades, components…"
              aria-label="Search material families and components"
              className="pl-8 pr-3 py-1.5 type-subhead border transition-all focus:outline-none"
              style={{
                borderRadius: 'var(--radius-full)',
                width: '200px',
                background: 'var(--color-bg-base)',
                borderColor: 'var(--color-border)',
                color: 'var(--color-text-primary)',
              }}
              onFocus={(e) => (e.currentTarget.style.width = '240px')}
              onBlur={(e) => (e.currentTarget.style.width = '200px')}
            />
          </div>

          {/* Theme toggle */}
          <button
            id="btn-toggle-theme"
            onClick={onToggleDarkMode}
            aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
            title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            className="press-target w-8 h-8 rounded-full flex items-center justify-center transition-colors"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            <span className="material-symbols-outlined text-[19px]">{isDarkMode ? 'light_mode' : 'dark_mode'}</span>
          </button>

          <div className="h-5 w-px mx-1" style={{ background: 'var(--color-border)' }} />

          {/* Notifications */}
          <div className="relative">
            <button
              id="btn-notifications"
              aria-label="Open notifications"
              onClick={() => setShowNotifications((v) => !v)}
              className="press-target relative w-8 h-8 flex items-center justify-center rounded-full transition-colors"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              <span className="material-symbols-outlined text-[20px]">notifications</span>
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full" style={{ background: 'var(--color-pass)' }} />
            </button>
            {showNotifications && <NotificationsDropdown onClose={() => setShowNotifications(false)} />}
          </div>

          {/* Avatar */}
          <button
            id="btn-topbar-avatar"
            onClick={() => onNavigate('settings')}
            aria-label="User settings"
            title="User Settings & Role Management"
            className="press-target w-8 h-8 rounded-full flex items-center justify-center border transition-all"
            style={{ background: 'var(--color-accent-subtle)', borderColor: 'var(--color-accent)', color: 'var(--color-accent)' }}
          >
            <span className="material-symbols-outlined text-[18px]">account_circle</span>
          </button>
        </div>
      </header>
    </>
  );
};
