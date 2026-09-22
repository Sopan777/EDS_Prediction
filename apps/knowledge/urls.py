from django.urls import path
from apps.knowledge.views import (
    knowledge_view,
    gate_editor_view,
    list_families_api,
    get_family_detail_api,
    GatesAPIView,
    ValidateGatesAPIView,
)

urlpatterns = [
    path('', knowledge_view, name='knowledge_index'),
    path('gates/<str:fid>/', gate_editor_view, name='gate_editor'),
    path('api/families', list_families_api, name='api_families'),
    path('api/families/<str:fid>', get_family_detail_api, name='api_family_detail'),
    path('api/gates', GatesAPIView.as_view(), name='api_gates'),
    path('api/gates/validate', ValidateGatesAPIView.as_view(), name='api_gates_validate'),
    path('api/gates/<str:fid>', GatesAPIView.as_view(), name='api_gates_family'),
]
