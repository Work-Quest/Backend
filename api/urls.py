import django.db
from django.urls import path
from api.views import *
from api.views.task_view import *
from api.views.game_view import *
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
    path("project/<uuid:project_id>/edit/", edit_project, name="edit_project"),
    path("project/delete/",batch_delete_projects,name="batch_delete_projects"),
    path("project/get_user_project/", get_projects, name="get_projects"),
    path("project/close/", close_project, name="close_project"),
    path("project/<uuid:project_id>/access/", check_project_access, name="check_project_access"),
    path("project/member/join/",join_project,name="join_project"),
    path("project/member/leave/",leave_project,name="leave_project"),
    path("project/<uuid:project_id>/members/",get_all_project_members,name="get_all_project_members"),
    # ----- Task URLs -----
    path("project/<uuid:project_id>/tasks/", task_list, name="task_list"),
    path("project/<uuid:project_id>/tasks/create/", task_create, name="task_create"),
    path("project/<uuid:project_id>/tasks/<uuid:task_id>/", task_detail, name="task_detail"),
    path("project/<uuid:project_id>/tasks/<uuid:task_id>/update/", task_update, name="task_update"),
    path("project/<uuid:project_id>/tasks/<uuid:task_id>/move/", task_move, name="task_move"),
    path("project/<uuid:project_id>/tasks/<uuid:task_id>/delete/", task_delete, name="task_delete"),
    path("project/<uuid:project_id>/tasks/<uuid:task_id>/assign/", task_assign, name="task_assign"),
    path("project/<uuid:project_id>/tasks/<uuid:task_id>/unassign/", task_unassign, name="task_unassign"),
    # ----- Game URLs -----
    path("game/bosses/", get_all_bosses, name="get_all_bosses"),
    path("game/project/<uuid:project_id>/boss/", get_project_boss, name="get_project_boss"),
    path("game/project/<uuid:project_id>/boss/setup/", setup_project_boss, name="setup_project_boss"),
    # path("game/project/<uuid:project_id>/boss/attack/", attack_boss, name="attack_boss"),
]