from collections import defaultdict
from django.db.models import QuerySet
from api.dtos.log_dto import ProjectLogReadDTO
from api.models import TaskLog


class TaskLogQueryService:
    """
    Read-only service.
    """

    def _base_queryset(self) -> QuerySet:
        return TaskLog.objects.all()

    def get_game_logs(self, project_id: str, time_begin=None) -> list[ProjectLogReadDTO]:
        """
        Get game-related logs for a project, optionally filtered by time.
        
        Args:
            project_id: Project ID to filter logs
            time_begin: Optional datetime to filter logs by created_at > time_begin
        """
        # Only return game-related events for the "game logs" endpoint.
        # (Avoid task lifecycle noise like TASK_CREATED / TASK_UPDATED / etc.)
        allowed_event_types = (
            TaskLog.EventType.USER_ATTACK,
            TaskLog.EventType.BOSS_ATTACK,
            TaskLog.EventType.KILL_BOSS,
            TaskLog.EventType.KILL_PLAYER,
            TaskLog.EventType.BOSS_REVIVE,
            TaskLog.EventType.USER_REVIVE,
        )
        logs = (
            self._base_queryset()
            .filter(project_id=project_id)
            .filter(event_type__in=allowed_event_types)
        )
        
        # Filter by time if provided
        if time_begin is not None:
            logs = logs.filter(created_at__gt=time_begin)
        
        logs = logs.order_by("-created_at")

        return [
            ProjectLogReadDTO(
                id=str(log.id),
                project_id=str(log.project_id),
                actor_type=log.actor_type,
                actor_id=(str(log.actor_id) if log.actor_id else None),
                event_type=log.event_type,
                payload=(log.payload or {}),
                created_at=log.created_at,
            )
            for log in logs
        ]

    # ---------- Grouping helpers ----------
    @staticmethod
    def group_logs_by_event_type(logs: list[ProjectLogReadDTO]) -> dict[str, list[ProjectLogReadDTO]]:
        """
        Group logs into buckets keyed by event_type (falls back to 'UNKNOWN').
        """
        grouped: dict[str, list[ProjectLogReadDTO]] = defaultdict(list)
        for log in logs:
            grouped[log.event_type or "UNKNOWN"].append(log)
        return dict(grouped)

    @staticmethod
    def group_logs_by_category(logs: list[ProjectLogReadDTO]) -> dict[str, list[ProjectLogReadDTO]]:
        """
        Group logs into higher-level categories based on event_type.
        """
        category_event_types: dict[str, set[str]] = {
            "TASK_LIFECYCLE": {
                TaskLog.EventType.TASK_CREATED,
                TaskLog.EventType.TASK_UPDATED,
                TaskLog.EventType.TASK_DELETED,
                TaskLog.EventType.TASK_COMPLETED,
                TaskLog.EventType.TASK_REVIEW,
                TaskLog.EventType.ASSIGN_USER,
                TaskLog.EventType.UNASSIGN_USER,
            },
            "COMBAT": {
                TaskLog.EventType.USER_ATTACK,
                TaskLog.EventType.BOSS_ATTACK,
                TaskLog.EventType.HEAL,
            },
            "EFFECTS": {
                TaskLog.EventType.APPLY_BUFF,
                TaskLog.EventType.APPLY_DEBUFF,
            },
            "ITEMS": {
                TaskLog.EventType.GIVE_ITEM,
                TaskLog.EventType.USE_ITEM,
            },
            "PROGRESSION": {
                TaskLog.EventType.KILL_BOSS,
                TaskLog.EventType.KILL_PLAYER,
            },
            "REVIVE": {
                TaskLog.EventType.USER_REVIVE,
                TaskLog.EventType.BOSS_REVIVE,
            },
            "BOSS_LIFECYCLE": {
                TaskLog.EventType.BOSS_NEXT_PHASE_SETUP,
            },
        }

        def _category_for(event_type: str | None) -> str:
            if not event_type:
                return "UNKNOWN"
            for category, event_types in category_event_types.items():
                if event_type in event_types:
                    return category
            return "OTHER"

        grouped: dict[str, list[ProjectLogReadDTO]] = defaultdict(list)
        for log in logs:
            grouped[_category_for(log.event_type)].append(log)
        return dict(grouped)

    def get_all_logs(self, *, time_begin=None) -> list[ProjectLogReadDTO]:
        """
        Get all TaskLogs, optionally filtered by created_at >= time_begin.

        Args:
            time_begin: datetime (timezone-aware recommended). If provided, filters logs by created_at__gte.
        """
        logs = self._base_queryset()
        if time_begin is not None:
            logs = logs.filter(created_at__gt=time_begin)
        logs = logs.order_by("-created_at")

        return [
            ProjectLogReadDTO(
                id=str(log.id),
                project_id=(str(log.project_id) if log.project_id else None),
                actor_type=log.actor_type,
                actor_id=(str(log.actor_id) if log.actor_id else None),
                event_type=log.event_type,
                payload=(log.payload or {}),
                created_at=log.created_at,
            )
            for log in logs
        ]
  