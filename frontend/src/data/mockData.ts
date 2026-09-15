/**
 * mockData.ts
 * ===========
 * This file now contains ONLY static configuration constants that are not
 * served from the backend API. All application data (families, users,
 * audit logs) comes from the Flask API at runtime.
 *
 * Removed:
 *   - INITIAL_MATERIAL_FAMILIES  (was 12 hardcoded families — now from /api/families)
 *   - INITIAL_USERS              (was 5 hardcoded users — now from /api/users)
 *   - INITIAL_AUDIT_LOGS         (was 3 hardcoded logs — now from /api/audit-logs)
 *   - External Google image URLs (METAL_MACRO_BG, AVATAR_* — removed; avatars use initials)
 *
 * Kept:
 *   - ROLE_DEFINITIONS: Static role metadata that describes the four role types.
 *     This is UI configuration, not application data, so it does not need a
 *     backend endpoint.
 */

import { RoleDefinition } from '../types';

export const ROLE_DEFINITIONS: RoleDefinition[] = [
  {
    id: 'role-snr-met',
    title: 'Snr. Metallurgist',
    description:
      'Full access to modify ratio gates, approve spectral deviations, and edit global Knowledge Base.',
    userCount: 1,
  },
  {
    id: 'role-lab-tech',
    title: 'Lab Tech',
    description:
      'Execute scans, log samples, and view historical data. Cannot alter baseline thresholds.',
    userCount: 2,
  },
  {
    id: 'role-auditor',
    title: 'Auditor',
    description:
      'Read-only access across all departments. Can export reports and view scan history.',
    userCount: 1,
  },
  {
    id: 'role-service',
    title: 'Service Acct / API',
    description:
      'Automated spectrometers and ETL ingest pipelines with programmatic execution rights.',
    userCount: 1,
  },
];
