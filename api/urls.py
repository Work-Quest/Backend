import django.db
from django.urls import path
from api.views import register, login, check_auth_status, me, logout, google_login, refresh_token
import rest_framework.decorators

urlpatterns = [
    path("auth/register/", register),
    path("auth/login/", login),
    path("auth/google/", google_login),
    path("auth/logout/", logout),
    path("auth/status/", check_auth_status),
    path("auth/refresh/", refresh_token),
    path("me/", me),
]
