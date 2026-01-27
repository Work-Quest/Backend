from django.db.models import QuerySet
from api.dtos.log_dto import GameLogReadDTO
from api.models import TaskLog
from django.db.models import Q


GAME_RELEVANT_EVENTS = [
    "USER_ATTACK",
    "BOSS_ATTACK",
    "APPLY_BUFF",
    "APPLY_DEBUFF",
    "GIVE_ITEM",
    "USE_ITEM",
    "HEAL",
    "KILL_BOSS",
    "KILL_PLAYER"
    ]

class TaskLogQueryService:
    """
    Read-only service.
    """

    def _base_queryset(self) -> QuerySet:
        return TaskLog.objects.select_related(
            "task",
            "task__project",
            "project_member",
            "project_member__project",
            "project_boss",
            "project_boss__project",
        )

    def get_game_logs(self, project_id) -> list[GameLogReadDTO]:
        # Get logs that are related to the project through:
        
        logs = (
            self._base_queryset()
            .filter(
                Q(task__project_id=project_id) |
                Q(project_member__project_id=project_id) |
                Q(project_boss__project_id=project_id)
            )
            .order_by("-created_at")
            .filter(event__in=GAME_RELEVANT_EVENTS)
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
