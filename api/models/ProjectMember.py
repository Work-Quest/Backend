from django.db import models
import uuid
from .Project import Project
from .User import User

class ProjectMember(models.Model):
    STATUS_CHOICES = [
        ('Alive', 'Alive'),
        ('Dead', 'Dead'),
    ]

    project_member_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects")
    hp = models.IntegerField(default=100)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Alive")
