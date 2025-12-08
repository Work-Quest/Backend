from django.db import models
import uuid
from .ProjectMember import ProjectMember

class UserAttack(models.Model):
    user_attack_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_member = models.ForeignKey(ProjectMember, on_delete=models.CASCADE, related_name="attacks")
    damage_point = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

