# views/project.py

import os
import django.contrib.auth.models
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from api.models import BusinessUser
from api.models.Project import Project as ProjectModel
from api.services.project_service import ProjectService
from api.services.join_service import JoinService
from api.serializers.project_serializer import ProjectSerializer, ProjectMemberSerializer
from api.services.cache_service import CacheService
from datetime import timedelta

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
        domain = ProjectService().create_project(request.data, user)
        serializer = ProjectSerializer(domain.project)
        CacheService().invalidate_user_projects(user.user_id)
        return Response(
            serializer.data,
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
        print("Editing project:", project_id, request.data)
        cur_user = request.user
        user = BusinessUser.objects.get(auth_user=cur_user)
        domain = ProjectService().edit_project(project_id, request.data, user)
        serializer = ProjectSerializer(domain.project)
        CacheService().invalidate_user_projects(user.user_id)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        print("Error editing project:", str(e))
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

    # Deleting projects changes the current user's project list.
    try:
        cur_user = request.user
        user = BusinessUser.objects.get(auth_user=cur_user)
        CacheService().invalidate_user_projects(user.user_id)
    except Exception:
        pass

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
    cache_svc = CacheService()
    cache_key = cache_svc.keys.user_projects(user.user_id)
    cached = cache_svc.get(cache_key)
    if cached is not None:
        data = cached
    else:
        data = list(
            ProjectSerializer(
                [d.project for d in ProjectService().get_projects(user.user_id)],
                many=True,
            ).data
        )
        cache_svc.set(cache_key, data, ttl_seconds=30)
    return Response(
        data,
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
    project_id = request.data.get("project_id")
    res = ProjectService().join_project(project_id, user)

    if not res.get("member"):
        err = res.get("message") or res.get("error") or "Failed to join project"
        status_code = status.HTTP_400_BAD_REQUEST
        if "not found" in str(err).lower():
            status_code = status.HTTP_404_NOT_FOUND
        return Response(
            {"error": err},
            status=status_code,
        )

    CacheService().invalidate_user_projects(user.user_id)
    CacheService().invalidate_project_members(project_id)

    serializer = ProjectMemberSerializer(res["member"])
    return Response(
        {
            "message": "Joined project successfully",
            "project_member": serializer.data,
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
    project_id = request.data.get("project_id")
    is_left = ProjectService().leave_project(project_id, user)
    if is_left:
        CacheService().invalidate_user_projects(user.user_id)
        CacheService().invalidate_project_members(project_id)
        return Response(
            {"message": "Left project successfully"},
            status=status.HTTP_200_OK,
        )
    return Response(
        {"message": "Failed to leave project"},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def batch_invite(request, project_id):
    """
    Batch invite people to a project by email.

    URL Param:
        project_id: UUID

    Request Body:

        {
            "user_ids": ["uuid", "uuid"],
            "expires_in_days": 2                               (optional)
        }
    """
    cur_user = request.user
    user = BusinessUser.objects.get(auth_user=cur_user)

    project = ProjectModel.objects.get(project_id=project_id)
    if project.owner != user:
        return Response(
            {"error": "Only the project owner can invite members."},
            status=status.HTTP_403_FORBIDDEN,
        )

    users = request.data.get("user_ids")
    emails = []
    for i in users:
        user = BusinessUser.objects.get(user_id=i)
        emails.append(user.email)

    # todo: env config
    if os.getenv("DB_ENV") == "prod" :
        invite_base_url ="https://workquest-1h39.onrender.com" 
    else:
        invite_base_url= "http://localhost:5173"
    expires_in_days = request.data.get("expires_in_days", 2)
    try:
        expires_in_days = int(expires_in_days)
    except Exception:
        expires_in_days = 2

    payload = JoinService().invite_players(
        request=request,
        project_id=project_id,
        emails=emails,
        invite_base_url=invite_base_url,
        expires_in=timedelta(days=max(1, expires_in_days)),
    )

    if payload.get("error"):
        return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    # If you later add caching for invites, invalidate it here.
    return Response(payload, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def close_project(request):
    """
    Close a project.

    This endpoint closes the specified project.

    Request Body:
    
        {
            "project_id": UUID  
        }
    """
    cur_user = request.user
    user = BusinessUser.objects.get(auth_user=cur_user)

    project_id = request.data.get("project_id")
    domain = ProjectService().close_project(project_id, user)
    serializer = ProjectSerializer(domain.project)
    CacheService().invalidate_user_projects(user.user_id)
    return Response(
        serializer.data,
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_project_access(request, project_id):
    """
    Check if the authenticated user has access to the specified project.
    """
    cur_user = request.user
    user = BusinessUser.objects.get(auth_user=cur_user)
    has_access = ProjectService().check_project_access(project_id, user)
    if has_access is None:
        return Response(
            {"error": "Project not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if has_access:
        return Response(
            {"message": "User has access to the project."},
            status=status.HTTP_200_OK,
        )
    return Response(
        {"message": "User does not have access to the project."},
        status=status.HTTP_403_FORBIDDEN,
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_all_project_members(request, project_id):
    """
    Retrieve all members of a specified project.
    """
    cache_svc = CacheService()

    def _load() -> list[dict]:
        members = ProjectService().get_all_project_members(project_id)
        members_data: list[dict] = []
        for i in members:
            metadata = {
                "id": i.project_member_id,
                "name": i.user.name,
                "username": i.user.username,
                "hp": i.hp,
                "status": i.status,
            }
            members_data.append(metadata)
        return members_data

    members_data = cache_svc.read_through(
        key=cache_svc.keys.project_members(project_id),
        ttl_seconds=10,
        loader=_load,
    )

    return Response(
        members_data,
        status=status.HTTP_200_OK
    )