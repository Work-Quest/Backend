from django.db import models
import uuid
from .ProjectMember import ProjectMember
from .Task import Task

class Report(models.Model):
    report_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="task")
    reporter = models.ForeignKey(ProjectMember, on_delete=models.CASCADE, related_name="reporter", null=True, blank=True )
    description = models.TextField()
    sentiment_score = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
