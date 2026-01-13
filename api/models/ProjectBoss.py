from django.db import models
import uuid
from .Project import Project
from .Boss import Boss

class ProjectBoss(models.Model):
    STATUS_CHOICES = [
        ('Alive', 'Alive'),
        ('Dead', 'Dead'),
    ]

    project_boss_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="bosses")
    boss = models.ForeignKey(Boss, on_delete=models.CASCADE, related_name="projects")
    hp = models.IntegerField(default=0)
    max_hp = models.IntegerField(default=1000)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Alive")

