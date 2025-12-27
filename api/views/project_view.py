# views/project.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from services.project_service import ProjectService
from models.project import Project as ProjectModel
from domains.project import ProjectDomain


# -------------------------
# Project CRUD
# -------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_project(request):
    domain = ProjectService().create_project(request.data)
    return Response(
        {
            "project_id": domain.project_model.id,
            "name": domain.project_model.name,
            "description": domain.project_model.description,
            "status": domain.project_model.status,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def edit_project(request, project_id):
    domain = ProjectService().edit_project(project_id, request.data)
    return Response(
        {
            "project_id": domain.project_model.id,
            "name": domain.project_model.name,
            "description": domain.project_model.description,
            "status": domain.project_model.status,
        },
        status=status.HTTP_200_OK,
    )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def batch_delete_projects(request):
    """
    Batch delete projects by project_ids
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
    domains = ProjectService().get_projects(request.user)
    return Response(
        [
            {
                "project_id": d.project_model.id,
                "name": d.project_model.name,
                "status": d.project_model.status,
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
def join_project(request, project_id):
    res = ProjectService().join_project(project_id, request.user)

    if not res["member"]:
        return Response(
            {"error": res["message"]},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        {
            "project_member_id": res["member"].project_member_id,
            "hp": res["member"].hp,
            "status": res["member"].status,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def leave_project(request, project_id):
    message = ProjectService().leave_project(project_id, request.user)

    return Response(
        {"message": message["message"]},
        status=status.HTTP_200_OK,
    )
