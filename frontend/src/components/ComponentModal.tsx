import React, { useEffect, useRef } from 'react';
import { CandidateComponent } from '../types';

interface ComponentModalProps {
  component: CandidateComponent | null;
  onClose: () => void;
  isDarkMode: boolean;
}

export const ComponentModal: React.FC<ComponentModalProps> = ({
  component,
  onClose,
  isDarkMode,
}) => {
  const panelRef = useRef<HTMLDivElement>(null);

  // Focus trap: focus first focusable element on mount
  useEffect(() => {
    if (!component) return;
    const el = panelRef.current?.querySelector<HTMLElement>(
      '[tabindex]:not([tabindex="-1"]), button, input, select, textarea, a[href]'
    );
    el?.focus();
  }, [component]);

  if (!component) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center modal-overlay p-4">
      {/* Entrance animation wrapper */}
      <div className="anim-spring-in">
        <div
          ref={panelRef}
          className="w-full max-w-lg p-6"
          style={{
            background: 'var(--color-bg-card)',
            border: '1px solid var(--color-border)',
            boxShadow: 'var(--shadow-modal)',
            borderRadius: 'var(--radius-xl)',
            color: 'var(--color-text-primary)',
          }}
        >
          {/* Header */}
          <div
            className="flex justify-between items-start mb-4 pb-3"
            style={{ borderBottom: '1px solid var(--color-border)' }}
          >
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="px-2 py-0.5 rounded text-[11px] font-mono-code font-bold"
                  style={{
                    background: 'var(--color-accent-subtle)',
                    color: 'var(--color-accent)',
                  }}
                >
                  {component.partNumber}
                </span>
                <span
                  className="text-[12px] opacity-60"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  • {component.category}
                </span>
              </div>
              <h3
                className="font-display text-[22px] font-bold"
                style={{ color: 'var(--color-text-primary)' }}
              >
                {component.name}
              </h3>
            </div>
            <button
              onClick={onClose}
              className="press-target p-1 rounded"
              style={{ color: 'var(--color-text-tertiary)' }}
            >
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>

          {/* Content details */}
          <div className="space-y-4 text-[13px]">
            <div className="grid grid-cols-2 gap-3">
              <div
                className="p-3 rounded-lg"
                style={{
                  background: 'var(--color-bg-elevated)',
                  border: '1px solid var(--color-border)',
                }}
              >
                <span
                  className="text-[11px] font-bold uppercase tracking-wider block mb-1 opacity-60"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  Nominal Metallurgy
                </span>
                <span
                  className="font-semibold"
                  style={{ color: 'var(--color-text-primary)' }}
                >
                  {component.nominalAlloy}
                </span>
              </div>
              <div
                className="p-3 rounded-lg"
                style={{
                  background: 'var(--color-bg-elevated)',
                  border: '1px solid var(--color-border)',
                }}
              >
                <span
                  className="text-[11px] font-bold uppercase tracking-wider block mb-1 opacity-60"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  Cross-Match Confidence
                </span>
                <span
                  className="font-mono-code font-bold text-[15px]"
                  style={{ color: 'var(--color-pass)' }}
                >
                  {component.confidence}%
                </span>
              </div>
            </div>

            <div
              className="p-3 rounded-lg"
              style={{
                background: 'var(--color-bg-elevated)',
                border: '1px solid var(--color-border)',
              }}
            >
              <h4
                className="text-[11px] font-bold uppercase tracking-wider mb-1.5 opacity-60"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                Laboratory Engineering Notes
              </h4>
              <p
                className="leading-relaxed"
                style={{ color: 'var(--color-text-primary)' }}
              >
                {component.notes ||
                  'High-friction contact face subject to cyclical fatigue wear. Particulate debris routinely correlates with standard austenitic stainless steel signatures.'}
              </p>
            </div>

            <div
              className="flex items-center justify-between py-2 text-[12px]"
              style={{ borderTop: '1px solid var(--color-border)' }}
            >
              <span
                className="opacity-70"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                ASTM Standard Ref: E1508 / E2142
              </span>
              <span
                className="font-mono-code"
                style={{ color: 'var(--color-text-tertiary)' }}
              >
                Spectral Library v2.4 Verified
              </span>
            </div>
          </div>

          {/* Footer */}
          <div className="mt-6 flex justify-end gap-2">
            <button
              onClick={onClose}
              className="press-target px-4 py-2 rounded-lg text-[13px] font-semibold"
              style={{
                border: '1px solid var(--color-border)',
                color: 'var(--color-text-secondary)',
              }}
            >
              Close
            </button>
            <button
              onClick={() => {
                alert(`Exporting CAD specs and metallurgical certificate for ${component.name} (${component.partNumber})...`);
                onClose();
              }}
              className="press-target px-4 py-2 rounded-lg text-[13px] font-semibold"
              style={{
                background: 'var(--color-accent)',
                color: 'var(--color-accent-on)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              Export Spec Sheet
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
