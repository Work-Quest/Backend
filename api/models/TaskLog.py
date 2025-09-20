from django.db import models
import uuid
from .Task import Task
from .ProjectMember import ProjectMember

class TaskLog(models.Model):
    ACTION_CHOICES = [
        ('Boss', 'Boss'),
        ('User', 'User'),
    ]

    log_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="logs")
    project_member = models.ForeignKey(ProjectMember, on_delete=models.CASCADE, related_name="logs")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    user_attack = models.ForeignKey("UserAttack", on_delete=models.SET_NULL, null=True, blank=True)
    boss_attack = models.ForeignKey("BossAttack", on_delete=models.SET_NULL, null=True, blank=True)

