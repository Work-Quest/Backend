from django.db.models import QuerySet
from api.dtos.log_dto import ProjectLogReadDTO
from api.models import TaskLog


class TaskLogQueryService:
    """
    Read-only service.
    """

    def _base_queryset(self) -> QuerySet:
        return TaskLog.objects.all()

    def get_game_logs(self, project_id: str) -> list[ProjectLogReadDTO]:
        # Only return game-related events for the "game logs" endpoint.
        # (Avoid task lifecycle noise like TASK_CREATED / TASK_UPDATED / etc.)
        allowed_event_types = (
            TaskLog.EventType.USER_ATTACK,
            TaskLog.EventType.BOSS_ATTACK,
            # TaskLog.EventType.HEAL,
            # TaskLog.EventType.KILL_BOSS,
            # TaskLog.EventType.KILL_PLAYER,
            # TaskLog.EventType.USER_REVIVE,
            # TaskLog.EventType.BOSS_REVIVE,
           
            # Boss progression.
            # TaskLog.EventType.BOSS_NEXT_PHASE_SETUP,
        )
        logs = (
            self._base_queryset()
            .filter(project_id=project_id)
            .filter(event_type__in=allowed_event_types)
            .order_by("-created_at")
        )

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
    # # ---------- ETL ----------
    # def get_logs_for_etl(
    #     self,
    #     *,
    #     since: datetime | None = None,
    #     until: datetime | None = None,
    # ) -> list[TaskLogETLDTO]:
    #     qs = self._base_queryset()

    #     if since:
    #         qs = qs.filter(created_at__gte=since)
    #     if until:
    #         qs = qs.filter(created_at__lt=until)

    #     return [
    #         TaskLogETLDTO(
    #             task_id=log.task_id,
    #             project_id=log.task.project_id,
    #             actor_id=log.actor_id,
    #             action=log.action,
    #             damage=log.damage,
    #             priority_snapshot=log.priority_snapshot,
    #             created_at=log.created_at,
    #         )
    #         for log in qs.iterator(chunk_size=2000)
    #     ]
