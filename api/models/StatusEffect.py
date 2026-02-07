import uuid
from django.db import models

from .Effect import Effect

# Todo: delete this after
class StatusEffect(models.Model):

    class EffectCategory(models.TextChoices):
        BUFF = "BUFF"
        DEBUFF = "DEBUFF"

    status_effect_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=100)

    description = models.TextField(blank=True)

    category = models.CharField(
        max_length=10,
        choices=EffectCategory.choices
    )

    effects = models.ManyToManyField(
        Effect,
        related_name="status_effects"
    )

    duration_turns = models.IntegerField(
        null=True, blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
