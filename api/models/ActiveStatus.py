import uuid
from django.db import models

from .StatusEffect import StatusEffect
from .ProjectMember import ProjectMember

class ActiveStatusEffect(models.Model):

    active_status_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    project_member = models.ForeignKey(
        ProjectMember,
        on_delete=models.CASCADE,
        related_name="active_statuses"
    )

    status_effect = models.ForeignKey(
        StatusEffect,
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(auto_now_add=True)
