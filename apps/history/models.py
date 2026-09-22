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
            return json.loads(self.candidate_components_json) if self.candidate_components_json else []
        except Exception:
            return []


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
