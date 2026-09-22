import json
from django.db import models

class Report(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    title = models.CharField(max_length=255)
    sample_id = models.CharField(max_length=128)
    lot_number = models.CharField(max_length=128, null=True, blank=True)
    customer = models.CharField(max_length=128, null=True, blank=True)
    analyst_id = models.CharField(max_length=64)
    analyst_name = models.CharField(max_length=128)
    created_at = models.CharField(max_length=32)
    source_type = models.CharField(max_length=32)
    source_filename = models.CharField(max_length=255, null=True, blank=True)
    raw_composition_json = models.TextField()
    normalized_composition_json = models.TextField()
    decision = models.CharField(max_length=32)
    family_id = models.CharField(max_length=32, null=True, blank=True)
    family_label = models.CharField(max_length=128, null=True, blank=True)
    grade_hint = models.CharField(max_length=128, null=True, blank=True)
    compatibility_pct = models.FloatField()
    candidates_json = models.TextField(null=True, blank=True)
    caveats_json = models.TextField(null=True, blank=True)
    analyst_notes = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=32, default='Completed')

    class Meta:
        db_table = 'reports'
        managed = False
        ordering = ['-created_at']

    def get_raw_composition(self):
        try:
            return json.loads(self.raw_composition_json)
        except Exception:
            return {}

    def get_normalized_composition(self):
        try:
            return json.loads(self.normalized_composition_json)
        except Exception:
            return []

    def get_candidates(self):
        try:
            return json.loads(self.candidates_json) if self.candidates_json else []
        except Exception:
            return []

    def get_caveats(self):
        try:
            return json.loads(self.caveats_json) if self.caveats_json else []
        except Exception:
            return []

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'sample_id': self.sample_id,
            'lot_number': self.lot_number,
            'customer': self.customer,
            'analyst_id': self.analyst_id,
            'analyst_name': self.analyst_name,
            'created_at': self.created_at,
            'source_type': self.source_type,
            'source_filename': self.source_filename,
            'raw_composition': self.get_raw_composition(),
            'normalized_composition': self.get_normalized_composition(),
            'decision': self.decision,
            'family_id': self.family_id,
            'family_label': self.family_label,
            'grade_hint': self.grade_hint,
            'compatibility_pct': self.compatibility_pct,
            'candidates': self.get_candidates(),
            'caveats': self.get_caveats(),
            'analyst_notes': self.analyst_notes,
            'status': self.status,
        }
