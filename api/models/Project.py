from django.db import models
import uuid
from .BusinessUser import BusinessUser

class Project(models.Model):
    STATUS_CHOICES = [
        ('Working', 'Working'),
        ('Done', 'Done'),
    ]

    project_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(BusinessUser, on_delete=models.CASCADE, related_name="owned_projects")
    project_name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(null=True, blank=True)
    total_tasks = models.IntegerField(default=0)
    completed_tasks = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Working")
    deadline_decision = models.CharField(max_length=20, choices=[('closed', 'Closed'), ('continued', 'Continued')], null=True, blank=True)
    deadline_decision_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self) -> str:
        return self.project_name