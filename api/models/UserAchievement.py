from django.db import models
from .BusinessUser import BusinessUser
from .Achievement import Achievement
from .Project import Project

class UserAchievement(models.Model):
    user = models.ForeignKey(BusinessUser, on_delete=models.CASCADE, related_name="achievements")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name="user_achievements")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="user_achievements")
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "achievement", "project")