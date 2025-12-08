from django.db import models
import uuid
from .BusinessUser import BusinessUser
from .Project import Project

class UserFeedback(models.Model):
    feedback_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(BusinessUser, on_delete=models.CASCADE, related_name="feedbacks")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="feedbacks")
    feedback_text = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)