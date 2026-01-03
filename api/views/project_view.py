# views/project.py

import django.contrib.auth.models
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from api.models import BusinessUser
from api.services.project_service import ProjectService


# -------------------------
# Project CRUD
# -------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_project(request):
    """
    Create a new project.

    This endpoint creates a new project owned by the authenticated user.

    Request Body:

        {
            "project_name" : string,
            "deadline" : datetime
        }

    """
    try:
        cur_user = request.user
        user = BusinessUser.objects.get(auth_user=cur_user)
        d = ProjectService().create_project(request.data, user)
        return Response(
            {   
                "message": "Project created successfully",
                "project_id": d.project.project_id,
                "project_name": d.project.project_name,
                "status": d.project.status,
                "owner_id": d.project.owner.user_id,
                "owner_name": d.project.owner.auth_user.username,
                "created_at": d.project.created_at,
                "deadline": d.project.deadline,
                "total_tasks": d.project.total_tasks,
                "completed_tasks": d.project.completed_tasks,
            },
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def edit_project(request, project_id):
    """
    Edit an existing project.

    This endpoint updates project information such as name or description.

     Request Body:

        {
            "project_name" : string,
            "deadline" : datetime,
            "status" : string ENUM("Working", "Done"),
            "total_tasks" : int,
            "completed_tasks" : int
        }

    """
    try:
        domain = ProjectService().edit_project(project_id, request.data)
        return Response(
            {
                "message": "Project updated successfully",
                "project_id": domain.project.project_id,
                "project_name" : domain.project.project_name,
                "deadline" : domain.project.deadline,
                "status" : domain.project.status,
                "total_tasks" : domain.project.total_tasks,
                "completed_tasks" : domain.project.completed_tasks
            },
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def batch_delete_projects(request):
    """
    Delete multiple projects in a single request.

    This endpoint allows batch deletion of projects owned by the authenticated user.

    Request Body:
    
        {
            "project_ids": [UUID1, UUID2, ...] 
        }
    """
    project_ids = request.data.get("project_ids")

    if not project_ids or not isinstance(project_ids, list):
        return Response(
            {"error": "project_ids must be a non-empty list"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    service = ProjectService()
    deleted = []
    failed = []

    for project_id in project_ids:
        try:
            service.delete_project(project_id)
            deleted.append(str(project_id))
        except Exception as e:
            failed.append({
                "project_id": str(project_id),
                "error": str(e),
            })

    return Response(
        {
            "deleted_projects": deleted,
            "failed_projects": failed,
        },
        status=status.HTTP_200_OK,
    )


# -------------------------
# Project Query
# -------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_projects(request):
    """
    Retrieve all projects of the authenticated user.
    """
    cur_user = request.user
    user = BusinessUser.objects.get(auth_user=cur_user)
    domains = ProjectService().get_projects(user.user_id)

    return Response(
        [
            {
                "project_id": d.project.project_id,
                "project_name": d.project.project_name,
                "status": d.project.status,
                "owner_id": d.project.owner.user_id,
                "owner_name": d.project.owner.auth_user.username,
                "created_at": d.project.created_at,
                "deadline": d.project.deadline,
                "total_tasks": d.project.total_tasks,
                "completed_tasks": d.project.completed_tasks,
            }
            for d in domains
        ],
        status=status.HTTP_200_OK,
    )


# -------------------------
# Project Member Actions
# -------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_project(request):
    """
    Join a project.

    This endpoint allows the authenticated user to join a project using its project ID.

    Request Body:
    
        {
            "project_id": UUID
        }
    """
    cur_user = request.user
    user = BusinessUser.objects.get(auth_user=cur_user)
    res = ProjectService().join_project(request.data.get("project_id"), user)

    if not res["member"]:
        return Response(
            {"error": res["message"]},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        {
            "message": "Joined project successfully",
            "project_member_id": res["member"].project_member_id,
            "hp": res["member"].hp,
            "status": res["member"].status,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def leave_project(request):
    """
    Leave a project.

    This endpoint removes the authenticated user from the specified project.

    Request Body:
    
        {
            "project_id": UUID
        }
    """
    cur_user = request.user
    user = BusinessUser.objects.get(auth_user=cur_user)
    message = ProjectService().leave_project(request.data.get("project_id"), user)

    return Response(
        {"message": message["message"]},
        status=status.HTTP_200_OK,
    )
