from django.db import models

from .Effect import Effect
from .ProjectMember import ProjectMember
import uuid

class UserEffect(models.Model):
    user_effect_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    project_member = models.ForeignKey(ProjectMember, on_delete=models.CASCADE)
    effect = models.ForeignKey(Effect, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)