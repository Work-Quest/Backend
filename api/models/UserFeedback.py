from django.db import models
import uuid
from .ProjectMember import ProjectMember
from .Project import Project

class UserFeedback(models.Model):
    feedback_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(ProjectMember, on_delete=models.CASCADE, related_name="feedbacks")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="feedbacks")
    feedback_text = models.TextField(null=True, blank=True)
    overall_quality_score = models.FloatField(null=True, blank=True)
    team_work = models.FloatField(null=True, blank=True)
    strength = models.TextField(null=True, blank=True)
    work_load_per_day= models.TextField(null=True, blank=True)
    work_speed= models.TextField(null=True, blank=True)
    role_assigned = models.TextField(null=True, blank=True)
    diligence = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)