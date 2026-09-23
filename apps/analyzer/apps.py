from django.apps import AppConfig

class AnalyzerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.analyzer'
    verbose_name = 'EDS Analyzer & Microanalysis'

    def ready(self):
        try:
            from database import init_db
            init_db()
        except Exception:
            pass
