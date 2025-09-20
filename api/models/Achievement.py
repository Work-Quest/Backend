from django.db import models
import uuid

class Achievement(models.Model):
    achievement_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=255)