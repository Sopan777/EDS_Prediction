from django.urls import path
from apps.analyzer.views import analyzer_view, health_api, AnalyzeAPIView, PresetsAPIView

urlpatterns = [
    path('', analyzer_view, name='analyzer_index'),
    path('analyzer/', analyzer_view, name='analyzer_page'),
    path('api/health', health_api, name='api_health'),
    path('api/analyze', AnalyzeAPIView.as_view(), name='api_analyze'),
    path('api/presets', PresetsAPIView.as_view(), name='api_presets'),
]
