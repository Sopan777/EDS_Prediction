from django.urls import path
from apps.users.views import users_view, UsersAPIView, UserDetailAPIView

urlpatterns = [
    path('', users_view, name='users_index'),
    path('api/users', UsersAPIView.as_view(), name='api_users'),
    path('api/users/<str:uid>', UserDetailAPIView.as_view(), name='api_user_detail'),
]
