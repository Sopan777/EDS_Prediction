from django.urls import path
from apps.history.views import history_view, AuditLogsAPIView, AnalysisHistoryAPIView

urlpatterns = [
    path('', history_view, name='history_index'),
    path('api/audit-logs', AuditLogsAPIView.as_view(), name='api_audit_logs'),
    path('api/history', AnalysisHistoryAPIView.as_view(), name='api_history'),
]
