from django.db.models import QuerySet
from api.dtos.log_dto import GameLogReadDTO
from api.models import TaskLog


class TaskLogQueryService:
    """
    Read-only service.
    """

    def _base_queryset(self) -> QuerySet:
        return TaskLog.objects.select_related(
            "task",
            "task__project",
        )

    def get_game_logs(self, project_id: int) -> list[GameLogReadDTO]:
        logs = (
            self._base_queryset()
            .filter(task__project_id=project_id)
            .order_by("-created_at")
        )

        return [
            GameLogReadDTO(
                task_id=log.task_id,
                project_member_id=log.project_member_id,
                received_project_member_id=log.recieved_project_member_id,
                project_boss_id=log.project_boss_id,
                action_type=log.action_type,
                event=log.event,
                damage_point=log.damage_point,
                score_change=log.score_change,
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
