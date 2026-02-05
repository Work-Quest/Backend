import uuid
from django.db import models

class Effect(models.Model):

    class EffectType(models.TextChoices):
        DAMAGE_BUFF = "DAMAGE_BUFF"
        DAMAGE_DEBUFF = "DAMAGE_DEBUFF"
        SCORE_BONUS = "SCORE_BONUS"
        SCORE_PENALTY = "SCORE_PENALTY"
        DEFENCE_BUFF = "DEFENCE_BUFF"
        DEFENCE_DEBUFF = "DEFENCE_DEBUFF"
        HEAL = "HEAL"

    effect_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    effect_type = models.CharField(
        max_length=50,
        choices=EffectType.choices
    )

    value = models.FloatField()

    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
