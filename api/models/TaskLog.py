from django.db import models
import uuid

from .ProjectBoss import ProjectBoss
from .Task import Task
from .ProjectMember import ProjectMember
from .Report import Report

class TaskLog(models.Model):

    class ActionType(models.TextChoices):
        USER = "USER"
        BOSS = "BOSS"
        SYSTEM = "SYSTEM"

    class Event(models.TextChoices):
        # --- Task lifecycle ---
        TASK_CREATED = "TASK_CREATED"
        TASK_UPDATED = "TASK_UPDATED"
        TASK_DELETED = "TASK_DELETED"
        TASK_COMPLETED = "TASK_COMPLETED"
        TASK_REVIEW = "TASK_REVIEW"
        ASSIGN_USER = "ASSIGN_USER"
        UNASSIGN_USER = "UNASSIGN_USER"

        # --- Game mechanics ---
        USER_ATTACK = "USER_ATTACK"
        BOSS_ATTACK = "BOSS_ATTACK"
        APPLY_BUFF = "APPLY_BUFF"
        APPLY_DEBUFF = "APPLY_DEBUFF"
        GIVE_ITEM = "GIVE_ITEM"
        USE_ITEM = "USE_ITEM"
        HEAL = "HEAL"
        KILL_BOSS = "KILL_BOSS"
        KILL_PLAYER = "KILL_PLAYER"
       


    log_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="logs",
        null=True, blank=True
    )

    project_member = models.ForeignKey(
        ProjectMember,
        on_delete=models.CASCADE,
        related_name="logs",
        null=True, blank=True
    )

    received_project_member = models.ForeignKey(
        ProjectMember,
        on_delete=models.CASCADE,
        related_name="received_logs",
        null=True, blank=True
    )

    project_boss = models.ForeignKey(
        ProjectBoss,
        on_delete=models.CASCADE,
        related_name="logs",
        null=True, blank=True
    )

    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="report",
        null=True, blank=True
    )

    action_type = models.CharField(
        max_length=10,
        choices=ActionType.choices,
        default=ActionType.SYSTEM
    )

    event = models.CharField(
        max_length=50,
        choices=Event.choices,
        default=Event.TASK_CREATED
    )
    task_priority_snapshot = models.IntegerField(null=True, blank=True)
    score_change = models.IntegerField(null=True, blank=True)
    damage_point = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
