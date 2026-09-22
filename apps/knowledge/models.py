import json
from django.db import models

class RatioGate(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    family_id = models.CharField(max_length=32)
    name = models.CharField(max_length=64)
    numerator = models.CharField(max_length=16)
    denominator = models.CharField(max_length=16)
    min_val = models.FloatField()
    max_val = models.FloatField()
    rationale = models.TextField(null=True, blank=True)
    enabled = models.IntegerField(default=1)
    updated_at = models.CharField(max_length=32)
    updated_by = models.CharField(max_length=128)

    class Meta:
        db_table = 'ratio_gates'
        managed = False

    def to_frontend_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'numerator': self.numerator,
            'denominator': self.denominator,
            'min': self.min_val,
            'max': self.max_val,
            'rationale': self.rationale or '',
            'enabled': bool(self.enabled),
            'updated_at': self.updated_at,
            'updated_by': self.updated_by,
        }


class AlloyPreset(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    name = models.CharField(max_length=128)
    category = models.CharField(max_length=64)
    description = models.TextField(null=True, blank=True)
    composition_json = models.TextField()
    created_by = models.CharField(max_length=128)
    created_at = models.CharField(max_length=32)

    class Meta:
        db_table = 'alloy_presets'
        managed = False
        ordering = ['name']

    def get_composition(self):
        try:
            return json.loads(self.composition_json)
        except Exception:
            return {}

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description or '',
            'composition': self.get_composition(),
            'created_by': self.created_by,
            'created_at': self.created_at,
        }
