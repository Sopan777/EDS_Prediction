import json
from django.db import models


class PredictionFeedback(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    timestamp = models.CharField(max_length=32)
    analysis_id = models.CharField(max_length=64, null=True, blank=True)
    spectrum_json = models.TextField()
    predicted_family = models.CharField(max_length=128)
    predicted_component = models.CharField(max_length=128, null=True, blank=True)
    confirmed_family = models.CharField(max_length=128)
    confirmed_component = models.CharField(max_length=128)
    status = models.CharField(max_length=32, default='confirmed')
    analyst_name = models.CharField(max_length=128, default='Lab Metallurgist')
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'prediction_feedback'
        managed = False
        ordering = ['-timestamp']

    def get_spectrum(self):
        try:
            return json.loads(self.spectrum_json)
        except Exception:
            return {}

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'analysis_id': self.analysis_id,
            'spectrum': self.get_spectrum(),
            'predicted_family': self.predicted_family,
            'predicted_component': self.predicted_component,
            'confirmed_family': self.confirmed_family,
            'confirmed_component': self.confirmed_component,
            'status': self.status,
            'analyst_name': self.analyst_name,
            'notes': self.notes,
        }
