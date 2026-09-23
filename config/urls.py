"""
config/urls.py
==============
Root URL configuration for Spectral Lab - MaterialID Django full-stack application.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.analyzer.views import (
    dashboard_view,
    analyzer_view,
    health_api,
    AnalyzeAPIView,
    PresetsAPIView,
    list_components_api,
    get_component_detail_api,
    validation_results_api,
)
from apps.knowledge.views import (
    knowledge_view,
    gate_editor_view,
    list_families_api,
    get_family_detail_api,
    GatesAPIView,
    ValidateGatesAPIView,
)
from apps.history.views import history_view, AuditLogsAPIView, AnalysisHistoryAPIView
from apps.users.views import users_view, UsersAPIView, UserDetailAPIView
from apps.reports.views import reports_view, ReportsAPIView
from apps.feedback.views import FeedbackAPIView

from django.views.generic.base import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'images/favicon.ico', permanent=True)),

    # Frontend Views (Full-Stack Django Templates)
    path('', dashboard_view, name='home'),
    path('dashboard/', dashboard_view, name='dashboard_page'),
    path('analyzer/', analyzer_view, name='analyzer_page'),
    path('knowledge/', knowledge_view, name='knowledge_page'),
    path('gates/<str:fid>/', gate_editor_view, name='gate_editor'),
    path('gates/<str:fid>/', gate_editor_view, name='gate_editor_page'),
    path('history/', history_view, name='history_page'),
    path('users/', users_view, name='users_page'),
    path('settings/', users_view, name='settings_page'),
    path('reports/', reports_view, name='reports_page'),

    # REST / JSON APIs (Backwards compatible with React and Python clients)
    path('api/health', health_api, name='api_health'),
    path('api/analyze', AnalyzeAPIView.as_view(), name='api_analyze'),
    path('api/presets', PresetsAPIView.as_view(), name='api_presets'),

    path('api/families', list_families_api, name='api_families'),
    path('api/families/<str:fid>', get_family_detail_api, name='api_family_detail'),
    path('api/gates', GatesAPIView.as_view(), name='api_gates'),
    path('api/gates/validate', ValidateGatesAPIView.as_view(), name='api_gates_validate'),
    path('api/gates/<str:fid>', GatesAPIView.as_view(), name='api_gates_family'),

    path('api/audit-logs', AuditLogsAPIView.as_view(), name='api_audit_logs'),
    path('api/history', AnalysisHistoryAPIView.as_view(), name='api_history'),

    path('api/users', UsersAPIView.as_view(), name='api_users'),
    path('api/users/<str:uid>', UserDetailAPIView.as_view(), name='api_user_detail'),

    path('api/components', list_components_api, name='api_components'),
    path('api/components/<str:cid>', get_component_detail_api, name='api_component_detail'),
    path('api/validate', validation_results_api, name='api_validate'),

    path('api/feedback', FeedbackAPIView.as_view(), name='api_feedback'),

    path('api/reports', ReportsAPIView.as_view(), name='api_reports'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT or settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
