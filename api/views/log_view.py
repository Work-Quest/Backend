# views/log_view.py
from dataclasses import asdict
from datetime import datetime, time

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from api.models import BusinessUser, Project
from api.services.log_service import TaskLogQueryService
from api.domains.project import Project as ProjectDomain
from api.services.cache_service import CacheService


def _parse_time_begin(raw):
    """
    Parse a `time_begin` query param into a timezone-aware datetime (UTC by default settings).

    Accepts:
    - ISO 8601 datetime (e.g. 2026-02-27T12:34:56Z / +00:00)
    - Date only (e.g. 2026-02-27) -> treated as 00:00:00 of that date
    """
    if raw is None:
        return None
    raw = raw.strip()
    if raw == "":
        return None

    dt = parse_datetime(raw)
    if dt is None:
        d = parse_date(raw)
        if d is None:
            raise ValueError("Invalid time_begin. Use ISO datetime (e.g. 2026-02-27T00:00:00Z) or date (e.g. 2026-02-27).")
        dt = datetime.combine(d, time.min)

    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


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

        cache_svc = CacheService()

        def _load() -> dict:
            log_service = TaskLogQueryService()
            # get_game_logs includes logs related to the project through tasks, project_members, or project_bosses
            logs = log_service.get_game_logs(project_id)
            logs_data = [asdict(log) for log in logs]
            return {
                "project_id": str(project_id),
                "logs": logs_data,
                "count": len(logs_data),
            }

        payload = cache_svc.read_through(
            key=cache_svc.keys.project_game_logs(project_id),
            ttl_seconds=5,
            loader=_load,
        )

        return Response(payload, status=status.HTTP_200_OK)
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_project_logs_grouped(request, project_id):
    """
    Get game logs grouped by:
    - group_by=event_type (default)
    - group_by=category
    """
    try:
        group_by = (request.query_params.get("group_by") or "event_type").strip()
        if group_by not in ("event_type", "category"):
            return Response(
                {"error": "Invalid group_by. Use 'event_type' or 'category'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        cache_svc = CacheService()

        def _load() -> dict:
            log_service = TaskLogQueryService()
            logs = log_service.get_game_logs(project_id)

            if group_by == "category":
                groups = log_service.group_logs_by_category(logs)
            else:
                groups = log_service.group_logs_by_event_type(logs)

            groups_data = {
                group_key: {
                    "count": len(group_logs),
                    "logs": [asdict(l) for l in group_logs],
                }
                for group_key, group_logs in groups.items()
            }

            return {
                "project_id": str(project_id),
                "group_by": group_by,
                "groups": groups_data,
                "total_count": len(logs),
            }

        payload = cache_svc.read_through(
            key=cache_svc.keys.project_game_logs_grouped(project_id, group_by),
            ttl_seconds=5,
            loader=_load,
        )

        return Response(payload, status=status.HTTP_200_OK)
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


@api_view(["GET"])
def get_all_task_logs(request):
    """
    Get all TaskLogs (across all projects), optionally filtered by a time range start.

    Query params:
    - time_begin: ISO 8601 datetime or date string; filters created_at >= time_begin
    """
    try:
        time_begin_raw = request.query_params.get("time_begin")
        time_begin = _parse_time_begin(time_begin_raw)

        log_service = TaskLogQueryService()
        logs = log_service.get_all_logs(time_begin=time_begin)
        logs_data = [asdict(log) for log in logs]

        return Response(
            {
                "time_begin": (time_begin.isoformat() if time_begin else None),
                "logs": logs_data,
                "count": len(logs_data),
            },
            status=status.HTTP_200_OK,
        )
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

