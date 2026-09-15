export type NavSection = 'analyzer' | 'history' | 'knowledge' | 'settings' | 'gate-editor';
export type TopTab = 'dashboard' | 'reports' | 'archive';

export interface ElementalComposition {
  cr?: number;
  ni?: number;
  mn?: number;
  si?: number;
  c?: number | null;
  fe?: number | 'Bal.';  // Fe can be a measured number or balance shorthand
  mo?: number;
  [element: string]: number | string | null | undefined;  // Allow arbitrary elements from EDS reports
}

export interface CandidateComponent {
  id: string;
  name: string;
  partNumber: string;  // Empty string when not in knowledge base
  category: string;
  nominalAlloy: string;
  confidence: number;
  notes?: string;
}

export interface RatioGate {
  id: string;
  name: string;
  numerator: string;
  denominator: string;
  min: number;
  max: number;
  rationale: string;
  enabled: boolean;
}

export interface ElementBand {
  element: string;
  role: 'Required' | 'Optional' | 'Trace';
  rangeMin: number;
  rangeMax: number;
  spectraSupport: number;
  barOffsetPct: number;
  barWidthPct: number;
}

export interface MaterialFamily {
  id: string;
  code: string;
  name: string;
  gradeHint: string;
  status: 'FIRM' | 'PROV';
  description: string;
  compatibilityScore: number | null;  // null until an analysis is run
  totalSpectra: number;
  passingSpectra: number | null;   // null — not computed in knowledge base
  failingSpectra: number | null;   // null — not computed in knowledge base
  elementBands: ElementBand[];
  ratioGates: RatioGate[];
  candidateComponents: CandidateComponent[];
  contextCaveats: {
    title: string;
    description: string;
    icon: string;
  }[];
}

export interface UserAccount {
  id: string;
  name: string;
  email: string;
  role: 'Snr. Metallurgist' | 'Lab Tech' | 'Auditor' | 'Service Acct' | 'SysAdmin';
  department: string;
  permissions: 'Full Edit' | 'Read-only' | 'System Execution' | 'Admin';
  avatarUrl?: string | null;
  initials?: string;
  isActive: boolean;
  lastActive?: string;
}

export interface RoleDefinition {
  id: string;
  title: string;
  description: string;
  userCount: number;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  user: string;
  userRole: string;
  action: string;
  actionType: 'Gate Edit' | 'Knowledge Base Update' | 'Override' | 'Calibration';
  familyCode: string;
  changeDetails: {
    from: string;
    to: string;
  };
  impactText: string;
  impactType: 'positive' | 'neutral' | 'warning';
}

export interface AnalysisRecord {
  id: string;
  timestamp: string;
  sourceType: string;
  filename?: string | null;
  composition: Record<string, number>;
  decision: 'identified' | 'ambiguous' | 'unknown';
  materialFamily?: string | null;
  gradeHint?: string | null;
  compatibility: number | null;
  compatibilityPct: number;
  candidateComponents: string[];
  processingTimeSec?: number | null;
  sessionId?: string | null;
}
