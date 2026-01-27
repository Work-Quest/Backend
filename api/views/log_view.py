# views/log_view.py
from dataclasses import asdict
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from api.models import BusinessUser, Project
from api.services.log_service import TaskLogQueryService
from api.domains.project import Project as ProjectDomain


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_project_logs(request, project_id):
    """
    Get all logs for a specific project.

    Returns logs including task lifecycle events and game mechanics events.
    """
    try:
        cur_user = request.user
        user = BusinessUser.objects.get(auth_user=cur_user)
        
        # Check if user has access to the project
        project = Project.objects.get(project_id=project_id)
        domain = ProjectDomain(project)
        if not domain.check_access(user):
            return Response(
                {"error": "User does not have access to this project"},
                status=status.HTTP_403_FORBIDDEN,
            )

        log_service = TaskLogQueryService()
        # get_game_logs includes logs related to the project through tasks, project_members, or project_bosses
        logs = log_service.get_game_logs(project_id)

        # Convert DTOs to dictionaries using asdict
        logs_data = [asdict(log) for log in logs]

        return Response(
            {
                "project_id": str(project_id),
                "logs": logs_data,
                "count": len(logs_data)
            },
            status=status.HTTP_200_OK,
        )
    except Project.DoesNotExist:
        return Response(
            {"error": "Project not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except BusinessUser.DoesNotExist:
        return Response(
            {"error": "User not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

