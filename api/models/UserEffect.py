from django.db import models

from .Effect import Effect
from .ProjectMember import ProjectMember

class UserEffect(models.Model):
    project_member = models.ForeignKey(ProjectMember, on_delete=models.CASCADE)
    effect = models.ForeignKey(Effect, on_delete=models.CASCADE)
