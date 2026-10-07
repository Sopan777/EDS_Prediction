import json
from django.db import models

class AnalysisHistory(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    timestamp = models.CharField(max_length=32)
    source_type = models.CharField(max_length=32)
    filename = models.CharField(max_length=255, null=True, blank=True)
    composition_json = models.TextField()
    decision = models.CharField(max_length=32)
    material_family = models.CharField(max_length=128, null=True, blank=True)
    grade_hint = models.CharField(max_length=128, null=True, blank=True)
    compatibility = models.FloatField(null=True, blank=True)
    candidate_components_json = models.TextField(null=True, blank=True)
    processing_time_s = models.FloatField(null=True, blank=True)
    full_result_json = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'analysis_history'
        managed = False
        ordering = ['-timestamp']

    def get_composition(self):
        try:
            return json.loads(self.composition_json)
        except Exception:
            return {}

    def get_candidates(self):
        try:
            raw = json.loads(self.candidate_components_json) if self.candidate_components_json else []
            if isinstance(raw, list):
                normalized = []
                for item in raw:
                    if isinstance(item, dict):
                        normalized.append(item)
                    elif isinstance(item, str):
                        normalized.append({'name': item})
                return normalized
            return []
        except Exception:
            return []

    def get_full_result(self):
        try:
            return json.loads(self.full_result_json) if self.full_result_json else None
        except Exception:
            return None

    @property
    def compatibility_pct(self):
        val = self.compatibility or 0.0
        if val <= 1.0:
            return round(val * 100)
        return round(val)

    @property
    def top_component_name(self):
        full = self.get_full_result()
        if isinstance(full, dict):
            top_c = full.get('topCandidate')
            if isinstance(top_c, dict) and top_c.get('name'):
                return top_c['name']
            per_spec = full.get('perSpectrum')
            if isinstance(per_spec, list) and per_spec:
                cands = per_spec[0].get('candidateComponents') or []
                if cands and isinstance(cands[0], dict):
                    return cands[0].get('name') or '—'
        cands = self.get_candidates()
        if cands and isinstance(cands[0], dict):
            return cands[0].get('name') or '—'
        return '—'

    @property
    def top_indirect_source_name(self):
        full = self.get_full_result()
        if isinstance(full, dict):
            ind = full.get('indirectSourcePrediction')
            if isinstance(ind, dict):
                top_ind = ind.get('topIndirectSource')
                if isinstance(top_ind, dict) and top_ind.get('partName'):
                    return f"{top_ind['partName']} ({top_ind.get('material', ind.get('indirectFamily', ''))})"
                if ind.get('statusLabel'):
                    return ind['statusLabel']
            per_spec = full.get('perSpectrum')
            if isinstance(per_spec, list) and per_spec:
                sp_ind = per_spec[0].get('indirectSourcePrediction') or {}
                top_ind = sp_ind.get('topIndirectSource')
                if isinstance(top_ind, dict) and top_ind.get('partName'):
                    return f"{top_ind['partName']} ({top_ind.get('material', sp_ind.get('indirectFamily', ''))})"
        return 'Unknown / Inconclusive'

    @property
    def spectra_count(self):
        full = self.get_full_result()
        if isinstance(full, dict):
            if full.get('spectraCount'):
                return int(full['spectraCount'])
            per_spec = full.get('perSpectrum')
            if isinstance(per_spec, list) and per_spec:
                return len(per_spec)
        return 1


class AuditLog(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    timestamp = models.CharField(max_length=32)
    user_id = models.CharField(max_length=64)
    user_name = models.CharField(max_length=128)
    user_role = models.CharField(max_length=64)
    action = models.TextField()
    action_type = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=128, null=True, blank=True)
    details_json = models.TextField(null=True, blank=True)
    impact_type = models.CharField(max_length=32, default='neutral')

    class Meta:
        db_table = 'audit_logs'
        managed = False
        ordering = ['-timestamp']

    def get_details(self):
        try:
            return json.loads(self.details_json) if self.details_json else {}
        except Exception:
            return {}

    def to_frontend_dict(self):
        details = self.get_details()
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'user': self.user_name,
            'userRole': self.user_role,
            'action': self.action,
            'actionType': self.action_type,
            'familyCode': self.entity_id or details.get('family_id') or 'All',
            'changeDetails': {
                'from': details.get('from', ''),
                'to': details.get('to', ''),
            },
            'impactText': details.get('impact_text', self.action),
            'impactType': self.impact_type,
        }
