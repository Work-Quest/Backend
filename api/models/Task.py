from django.db import models
import uuid
from .Project import Project

class Task(models.Model):
    STATUS_CHOICES = [
        ('Todo', 'Todo'),
        ('InProgress', 'In Progress'),
        ('Finish', 'Finish'),
    ]

    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    type = models.CharField(max_length=50)
    priority = models.IntegerField(default=0)
    task_name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Todo")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)