import uuid
from django.db import models

from .StatusEffect import StatusEffect

class Item(models.Model):
    item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status_effects = models.ManyToManyField(
        StatusEffect,
        blank=True,
        related_name="items"
    )
    created_at = models.DateTimeField(auto_now_add=True)
