import django.db
from django.urls import path
from api.views import register, login, check_auth_status, me, logout
import rest_framework.decorators

urlpatterns = [
    path("auth/register/", register),
    path("auth/login/", login),
    path("auth/logout/", logout),
    path("auth/status/", check_auth_status),
    path("me/", me),
]
