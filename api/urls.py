import django.db
from django.urls import path
from api.views import *
import rest_framework.decorators

urlpatterns = [
    path("auth/register/", register),
    path("auth/login/", login),
    path("auth/google/", google_login),
    path("auth/logout/", logout),
    path("auth/status/", check_auth_status),
    path("auth/refresh/", refresh_token),
    path("me/", me),
    path("project/create", create_project, name="create_project"),
    path("project/edit/<uuid:project_id>", edit_project, name="edit_project"),
    path("project/delete/batch",batch_delete_projects,name="batch_delete_projects"),
    path("project/get", get_projects, name="get_projects"),
    path("project/member/join/<uuid:project_id>",join_project,name="join_project"),
    path( "project/member/leave/<uuid:project_id>",leave_project,name="leave_project"),
]
