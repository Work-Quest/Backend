from django.db import models
import uuid

class Boss(models.Model):
    boss_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    boss_name = models.CharField(max_length=100)
    boss_image = models.CharField(max_length=255)
