import uuid
from django.db import models
from django.conf import settings

class ActivityLog(models.Model):
    class Action(models.TextChoices):
        TASK_CREATED = "TASK_CREATED"
        TASK_UPDATED = "TASK_UPDATED"
        TASK_DELETED = "TASK_DELETED"

    activity_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="activities"
    )

    project_id = models.UUIDField()
    target_type = models.CharField(max_length=50)  # "Task"
    target_id = models.UUIDField()

    action = models.CharField(max_length=50, choices=Action.choices)

    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["project_id"]),
            models.Index(fields=["target_id"]),
            models.Index(fields=["created_at"]),
        ]
