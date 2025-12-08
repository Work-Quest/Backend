from django.db import models
from .ProjectMember import ProjectMember
from .Task import Task

class UserTask(models.Model):
    """Many-to-Many between ProjectMember and Task"""
    project_member = models.ForeignKey(ProjectMember, on_delete=models.CASCADE, related_name="tasks")
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="assigned_members")

    class Meta:
        unique_together = ("project_member", "task")