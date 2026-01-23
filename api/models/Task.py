from django.db import models
import uuid
from .Project import Project

class Task(models.Model):
    STATUS_CHOICES = [
        ('backlog', 'backlog'),
        ('todo', 'todo'),
        ('inProgress', 'in Progress'),
        ('done', 'done'),
    ]

    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    priority = models.IntegerField(default=1)
    task_name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Todo")
    deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)