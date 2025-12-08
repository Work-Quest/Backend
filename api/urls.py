from django.urls import path
from api.views import register, login
import rest_framework.decorators

urlpatterns = [
    path("auth/register/", register),
    path("auth/login/", login),
]
