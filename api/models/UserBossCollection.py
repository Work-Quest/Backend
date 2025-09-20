from django.db import models
from .User import User
from .Boss import Boss
from .Project import Project

class UserBossCollection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="boss_collections")
    boss = models.ForeignKey(Boss, on_delete=models.CASCADE, related_name="user_collections")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="user_boss_collections")
    defeat_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "boss", "project")