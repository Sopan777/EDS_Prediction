import React, { useState } from 'react';
import { AuditLogEntry, MaterialFamily } from '../types';
import { AuditLogView } from './AuditLogView';

interface SettingsViewProps {
  isDarkMode: boolean;
  onToggleTheme: () => void;
  auditLogs: AuditLogEntry[];
  families: MaterialFamily[];
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  isDarkMode,
  onToggleTheme,
  auditLogs,
  families,
}) => {
  const [activeTab, setActiveTab] = useState<'system' | 'audit'>('system');

  const totalGates = families.reduce(
    (acc, f) => acc + (f.ratioGates ? f.ratioGates.length : 0),
    0
  );

  return (
    <div id="settings-screen" className="flex flex-col gap-5 h-full overflow-y-auto pb-6 pr-1">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="type-display" style={{ color: 'var(--color-text-primary)' }}>
            System Settings & Diagnostics
          </h2>
          <p className="type-subhead mt-1" style={{ color: 'var(--color-text-secondary)' }}>
            Engine parameters, knowledge base specifications, operational storage, and activity audit trace.
          </p>
        </div>

        {/* Segmented Control */}
        <div
          className="flex p-1 gap-1 border self-start sm:self-auto"
          style={{
            borderRadius: 'var(--radius-lg)',
            background: 'var(--color-bg-card)',
            borderColor: 'var(--color-border)',
            boxShadow: 'var(--shadow-card)',
          }}
        >
          <button
            onClick={() => setActiveTab('system')}
            className={`press-target px-4 py-1.5 text-[13px] font-semibold transition-all ${
              activeTab === 'system' ? 'shadow-sm' : ''
            }`}
            style={{
              borderRadius: 'var(--radius-md)',
              background: activeTab === 'system' ? 'var(--color-accent)' : 'transparent',
              color: activeTab === 'system' ? 'var(--color-accent-on)' : 'var(--color-text-secondary)',
            }}
          >
            System & Engine
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`press-target px-4 py-1.5 text-[13px] font-semibold transition-all ${
              activeTab === 'audit' ? 'shadow-sm' : ''
            }`}
            style={{
              borderRadius: 'var(--radius-md)',
              background: activeTab === 'audit' ? 'var(--color-accent)' : 'transparent',
              color: activeTab === 'audit' ? 'var(--color-accent-on)' : 'var(--color-text-secondary)',
            }}
          >
            Audit Log ({auditLogs.length})
          </button>
        </div>
      </div>

      {/* Tab: System Configuration & Diagnostics */}
      {activeTab === 'system' && (
        <div className="flex flex-col gap-5 anim-spring-in">
          {/* 4 Summary Stat Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div
              className="p-5 border transition-all"
              style={{
                background: 'var(--color-bg-card)',
                borderColor: 'var(--color-border)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              <div className="flex justify-between items-start mb-3">
                <span className="type-caption" style={{ color: 'var(--color-text-tertiary)' }}>
                  Inference Engine
                </span>
                <span
                  className="p-1.5 border"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-pass-subtle)',
                    borderColor: 'var(--color-pass)',
                    color: 'var(--color-pass)',
                  }}
                >
                  <span className="material-symbols-outlined text-[18px]">verified</span>
                </span>
              </div>
              <div className="font-display text-[26px] font-bold" style={{ color: 'var(--color-text-primary)' }}>
                Rule Engine
              </div>
              <div className="type-caption mt-1" style={{ color: 'var(--color-pass)' }}>
                Deterministic · Active
              </div>
            </div>

            <div
              className="p-5 border transition-all"
              style={{
                background: 'var(--color-bg-card)',
                borderColor: 'var(--color-border)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              <div className="flex justify-between items-start mb-3">
                <span className="type-caption" style={{ color: 'var(--color-text-tertiary)' }}>
                  Material Families
                </span>
                <span
                  className="p-1.5 border"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-accent-subtle)',
                    borderColor: 'var(--color-border)',
                    color: 'var(--color-accent)',
                  }}
                >
                  <span className="material-symbols-outlined text-[18px]">menu_book</span>
                </span>
              </div>
              <div className="font-display text-[26px] font-bold" style={{ color: 'var(--color-text-primary)' }}>
                {families.length} Families
              </div>
              <div className="type-caption mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                From materials.json
              </div>
            </div>

            <div
              className="p-5 border transition-all"
              style={{
                background: 'var(--color-bg-card)',
                borderColor: 'var(--color-border)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              <div className="flex justify-between items-start mb-3">
                <span className="type-caption" style={{ color: 'var(--color-text-tertiary)' }}>
                  Custom Ratio Gates
                </span>
                <span
                  className="p-1.5 border"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-warn-subtle)',
                    borderColor: 'var(--color-warn)',
                    color: 'var(--color-warn)',
                  }}
                >
                  <span className="material-symbols-outlined text-[18px]">tune</span>
                </span>
              </div>
              <div className="font-display text-[26px] font-bold" style={{ color: 'var(--color-text-primary)' }}>
                {totalGates} Gates
              </div>
              <div className="type-caption mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                SQLite persistent
              </div>
            </div>

            <div
              className="p-5 border transition-all"
              style={{
                background: 'var(--color-bg-card)',
                borderColor: 'var(--color-border)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              <div className="flex justify-between items-start mb-3">
                <span className="type-caption" style={{ color: 'var(--color-text-tertiary)' }}>
                  Audit Events
                </span>
                <span
                  className="p-1.5 border"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-bg-elevated)',
                    borderColor: 'var(--color-border)',
                    color: 'var(--color-text-secondary)',
                  }}
                >
                  <span className="material-symbols-outlined text-[18px]">receipt_long</span>
                </span>
              </div>
              <div className="font-display text-[26px] font-bold" style={{ color: 'var(--color-text-primary)' }}>
                {auditLogs.length} Events
              </div>
              <div className="type-caption mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                Immutable change log
              </div>
            </div>
          </div>

          {/* Configuration Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Rule Engine & Metallurgical Ingestion */}
            <div
              className="p-6 border flex flex-col gap-4"
              style={{
                background: 'var(--color-bg-card)',
                borderColor: 'var(--color-border)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              <div className="flex items-center gap-2.5 pb-3 border-b" style={{ borderColor: 'var(--color-border)' }}>
                <span className="material-symbols-outlined text-[22px]" style={{ color: 'var(--color-accent)' }}>
                  science
                </span>
                <div>
                  <h3 className="type-headline" style={{ color: 'var(--color-text-primary)' }}>
                    Inference & Metallurgical Protocol
                  </h3>
                  <p className="type-caption" style={{ color: 'var(--color-text-tertiary)' }}>
                    Deterministic mathematical invariants and boundary checking
                  </p>
                </div>
              </div>

              <div className="space-y-3 text-[13px]">
                <div
                  className="p-3 border flex justify-between items-center"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-bg-base)',
                    borderColor: 'var(--color-border)',
                  }}
                >
                  <div>
                    <span className="font-semibold block" style={{ color: 'var(--color-text-primary)' }}>
                      Contamination Invariance
                    </span>
                    <span className="type-caption block" style={{ color: 'var(--color-text-tertiary)' }}>
                      Carbon tape adhesive & surface oxide C, O excluded from metal basis
                    </span>
                  </div>
                  <span
                    className="px-2.5 py-0.5 font-mono-code text-[11px] font-semibold border"
                    style={{
                      borderRadius: 'var(--radius-full)',
                      background: 'var(--color-pass-subtle)',
                      borderColor: 'var(--color-pass)',
                      color: 'var(--color-pass)',
                    }}
                  >
                    Active
                  </span>
                </div>

                <div
                  className="p-3 border flex justify-between items-center"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-bg-base)',
                    borderColor: 'var(--color-border)',
                  }}
                >
                  <div>
                    <span className="font-semibold block" style={{ color: 'var(--color-text-primary)' }}>
                      Safe Abstention Protocol
                    </span>
                    <span className="type-caption block" style={{ color: 'var(--color-text-tertiary)' }}>
                      Returns UNKNOWN when total metallic weight &lt; 50% or data is sparse
                    </span>
                  </div>
                  <span
                    className="px-2.5 py-0.5 font-mono-code text-[11px] font-semibold border"
                    style={{
                      borderRadius: 'var(--radius-full)',
                      background: 'var(--color-pass-subtle)',
                      borderColor: 'var(--color-pass)',
                      color: 'var(--color-pass)',
                    }}
                  >
                    Enforced
                  </span>
                </div>

                <div
                  className="p-3 border flex justify-between items-center"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-bg-base)',
                    borderColor: 'var(--color-border)',
                  }}
                >
                  <div>
                    <span className="font-semibold block" style={{ color: 'var(--color-text-primary)' }}>
                      Multi-Table Particle Pooling
                    </span>
                    <span className="type-caption block" style={{ color: 'var(--color-text-tertiary)' }}>
                      Combines multiple spectrum spots across PDF tables via predict_particle()
                    </span>
                  </div>
                  <span
                    className="px-2.5 py-0.5 font-mono-code text-[11px] font-semibold border"
                    style={{
                      borderRadius: 'var(--radius-full)',
                      background: 'var(--color-pass-subtle)',
                      borderColor: 'var(--color-pass)',
                      color: 'var(--color-pass)',
                    }}
                  >
                    Enabled
                  </span>
                </div>
              </div>
            </div>

            {/* Storage & Environment */}
            <div
              className="p-6 border flex flex-col gap-4"
              style={{
                background: 'var(--color-bg-card)',
                borderColor: 'var(--color-border)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              <div className="flex items-center gap-2.5 pb-3 border-b" style={{ borderColor: 'var(--color-border)' }}>
                <span className="material-symbols-outlined text-[22px]" style={{ color: 'var(--color-accent)' }}>
                  database
                </span>
                <div>
                  <h3 className="type-headline" style={{ color: 'var(--color-text-primary)' }}>
                    Persistence & Infrastructure
                  </h3>
                  <p className="type-caption" style={{ color: 'var(--color-text-tertiary)' }}>
                    Database connectivity, document uploads, and appearance
                  </p>
                </div>
              </div>

              <div className="space-y-3 text-[13px]">
                <div
                  className="p-3 border flex justify-between items-center"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-bg-base)',
                    borderColor: 'var(--color-border)',
                  }}
                >
                  <div>
                    <span className="font-semibold block" style={{ color: 'var(--color-text-primary)' }}>
                      SQLite Database
                    </span>
                    <span className="type-caption font-mono-code block" style={{ color: 'var(--color-text-tertiary)' }}>
                      spectral_lab.db (Persistent Storage)
                    </span>
                  </div>
                  <span
                    className="px-2.5 py-0.5 font-mono-code text-[11px] font-semibold border"
                    style={{
                      borderRadius: 'var(--radius-full)',
                      background: 'var(--color-pass-subtle)',
                      borderColor: 'var(--color-pass)',
                      color: 'var(--color-pass)',
                    }}
                  >
                    Connected
                  </span>
                </div>

                <div
                  className="p-3 border flex justify-between items-center"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-bg-base)',
                    borderColor: 'var(--color-border)',
                  }}
                >
                  <div>
                    <span className="font-semibold block" style={{ color: 'var(--color-text-primary)' }}>
                      Document Ingestion Store
                    </span>
                    <span className="type-caption font-mono-code block" style={{ color: 'var(--color-text-tertiary)' }}>
                      uploads/ (PDF / DOCX / Text)
                    </span>
                  </div>
                  <span
                    className="px-2.5 py-0.5 font-mono-code text-[11px] font-semibold border"
                    style={{
                      borderRadius: 'var(--radius-full)',
                      background: 'var(--color-accent-subtle)',
                      borderColor: 'var(--color-border)',
                      color: 'var(--color-accent)',
                    }}
                  >
                    Ready
                  </span>
                </div>

                <div
                  className="p-3 border flex justify-between items-center"
                  style={{
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-bg-base)',
                    borderColor: 'var(--color-border)',
                  }}
                >
                  <div>
                    <span className="font-semibold block" style={{ color: 'var(--color-text-primary)' }}>
                      Interface Appearance
                    </span>
                    <span className="type-caption block" style={{ color: 'var(--color-text-tertiary)' }}>
                      Currently in {isDarkMode ? 'Dark Navy' : 'Light Clean'} mode
                    </span>
                  </div>
                  <button
                    onClick={onToggleTheme}
                    className="press-target px-3 py-1 text-[12px] font-semibold border flex items-center gap-1.5 transition-all"
                    style={{
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--color-bg-card)',
                      borderColor: 'var(--color-border)',
                      color: 'var(--color-text-primary)',
                    }}
                  >
                    <span className="material-symbols-outlined text-[16px]">
                      {isDarkMode ? 'light_mode' : 'dark_mode'}
                    </span>
                    Switch to {isDarkMode ? 'Light' : 'Dark'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Audit Log */}
      {activeTab === 'audit' && (
        <div className="flex-1 anim-spring-in">
          <AuditLogView isDarkMode={isDarkMode} auditLogs={auditLogs} />
        </div>
      )}
    </div>
  );
};
