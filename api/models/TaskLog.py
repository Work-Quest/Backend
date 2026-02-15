from __future__ import annotations

import uuid

from django.db import models


class TaskLog(models.Model):

    class ActorType(models.TextChoices):
        USER = "user"
        BOSS = "boss"
        SYSTEM = "system"

    class EventType(models.TextChoices):
        # Task lifecycle
        TASK_CREATED = "TASK_CREATED"
        TASK_UPDATED = "TASK_UPDATED"
        TASK_DELETED = "TASK_DELETED"
        TASK_COMPLETED = "TASK_COMPLETED"
        TASK_REVIEW = "TASK_REVIEW"
        ASSIGN_USER = "ASSIGN_USER"
        UNASSIGN_USER = "UNASSIGN_USER"

        # Combat
        USER_ATTACK = "USER_ATTACK"
        BOSS_ATTACK = "BOSS_ATTACK"
        HEAL = "HEAL"

        # Effects
        APPLY_BUFF = "APPLY_BUFF"
        APPLY_DEBUFF = "APPLY_DEBUFF"

        # Items
        GIVE_ITEM = "GIVE_ITEM"
        USE_ITEM = "USE_ITEM"

        # Progression
        KILL_BOSS = "KILL_BOSS"
        KILL_PLAYER = "KILL_PLAYER"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_id = models.UUIDField(db_index=True, blank=True, null=True)

    actor_type = models.CharField(max_length=10, choices=ActorType.choices, default=ActorType.USER)
    actor_id = models.UUIDField(null=True, blank=True)

    event_type = models.CharField(max_length=50, choices=EventType.choices, db_index=True, blank=True, null=True)
    payload = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["project_id", "created_at"]),
            models.Index(fields=["project_id", "event_type", "created_at"]),
        ]

    @classmethod
    def write(
        cls,
        *,
        project_id,
        actor_type: str,
        actor_id=None,
        event_type: str,
        payload: dict | None = None,
    ) -> "TaskLog":
        return cls.objects.create(
            project_id=project_id,
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=event_type,
            payload=(payload or {}),
        )
