export type NavSection = 'analyzer' | 'history' | 'knowledge' | 'settings' | 'gate-editor';
export type TopTab = 'dashboard' | 'reports' | 'archive';

export interface ElementalComposition {
  cr: number;
  ni: number;
  mn: number;
  si: number;
  c?: number | null;
  fe?: string;
  mo?: number;
}

export interface CandidateComponent {
  id: string;
  name: string;
  partNumber: string;
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
  compatibilityScore: number;
  totalSpectra: number;
  passingSpectra: number;
  failingSpectra: number;
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
  department: 'Research' | 'Operations' | 'System' | 'Quality Control' | 'Metallurgy';
  permissions: 'Full Edit' | 'Read-only' | 'System Execution' | 'Admin';
  avatarUrl?: string;
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
