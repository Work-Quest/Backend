from django.db import models
import uuid
from .Task import Task
from .ProjectMember import ProjectMember
from .UserAttack import UserAttack
from .BossAttack import BossAttack

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
        ASSIGN_USER = "ASSIGN_USER"
        UNASSIGN_USER = "UNASSIGN_USER"

        # --- Game mechanics ---
        USER_ATTACK = "USER_ATTACK"
        BOSS_ATTACK = "BOSS_ATTACK"
        APPLY_BUFF = "APPLY_BUFF"
        APPLY_DEBUFF = "APPLY_DEBUFF"
        GIVE_ITEM = "GIVE_ITEM"
        BUFF_APPLIED = "BUFF_APPLIED"
        DEBUFF_APPLIED = "DEBUFF_APPLIED"
        RECIEVE_ITEM = "RECIEVE_ITEM"
        USE_ITEN = "USE_ITEM"


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

    # --- combat specific ---
    user_attack = models.ForeignKey(
        UserAttack,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    boss_attack = models.ForeignKey(
        BossAttack,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
