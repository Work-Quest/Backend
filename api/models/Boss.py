from django.db import models
import uuid

class Boss(models.Model):
    BOSS_TYPE = [
        ('Normal', 'Normal'),
        ('Special', 'Special'),
    ]

    boss_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    boss_name = models.CharField(max_length=100)
    boss_type = models.CharField(max_length=50, choices=BOSS_TYPE, default='Normal')
    boss_image = models.CharField(max_length=255)
