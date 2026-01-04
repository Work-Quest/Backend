import django.db
from django.urls import path
from api.views import *
from api.views.task_view import task_list, task_create, task_detail, task_update, task_delete, task_assign, task_unassign
import rest_framework.decorators

urlpatterns = [
     # ----- Auth URLs -----
    path("auth/register/", register),
    path("auth/login/", login),
    path("auth/google/", google_login),
    path("auth/logout/", logout),
    path("auth/status/", check_auth_status),
    path("auth/refresh/", refresh_token),
    path("me/", me),
    # ----- Project URLs -----
    path("project/create/", create_project, name="create_project"),
    path("project/edit/<uuid:project_id>/", edit_project, name="edit_project"),
    path("project/delete/",batch_delete_projects,name="batch_delete_projects"),
    path("project/get_user_project/", get_projects, name="get_projects"),
    path("project/close/", close_project, name="close_project"),
    path("project/access/<uuid:project_id>/", check_project_access, name="check_project_access"),
    path("project/member/join/",join_project,name="join_project"),
    path("project/member/leave/",leave_project,name="leave_project"),
    # ----- Task URLs -----
    path("project/<uuid:project_id>/tasks/", task_list, name="task_list"),
    path("project/<uuid:project_id>/tasks/create/", task_create, name="task_create"),
    path("project/<uuid:project_id>/tasks/<uuid:task_id>/", task_detail, name="task_detail"),
    path("project/<uuid:project_id>/tasks/<uuid:task_id>/update/", task_update, name="task_update"),
    path("project/<uuid:project_id>/tasks/<uuid:task_id>/delete/", task_delete, name="task_delete"),
    path("project/<uuid:project_id>/tasks/<uuid:task_id>/assign/", task_assign, name="task_assign"),
    path("project/<uuid:project_id>/tasks/<uuid:task_id>/unassign/", task_unassign, name="task_unassign"),
]