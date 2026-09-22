from django.urls import path
from apps.reports.views import reports_view, ReportsAPIView

urlpatterns = [
    path('', reports_view, name='reports_index'),
    path('api/reports', ReportsAPIView.as_view(), name='api_reports'),
]
