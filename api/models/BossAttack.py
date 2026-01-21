from django.db import models
import uuid
from .ProjectBoss import ProjectBoss

class BossAttack(models.Model):
    boss_attack_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_boss = models.ForeignKey(ProjectBoss, on_delete=models.CASCADE, related_name="attacks")
    damage_point = models.IntegerField()
    project_member = models.ForeignKey('ProjectMember', on_delete=models.CASCADE, related_name="boss_attacks", null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
