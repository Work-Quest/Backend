import uuid
from django.db import models

from .Effect import Effect

class Item(models.Model):
    item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    effects = models.ForeignKey(
        Effect,
        blank=True,
        null=True,
        related_name="items",
        on_delete=models.DO_NOTHING
    )
    created_at = models.DateTimeField(auto_now_add=True)
