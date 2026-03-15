
from django.db import models

class ProjectEndSummary(models.Model):

    project_member_id = models.UUIDField(primary_key=True)

    project_id = models.UUIDField(db_index=True)

    user_id = models.UUIDField(db_index=True)

    order = models.IntegerField()

    name = models.CharField(max_length=255)
    username = models.CharField(max_length=255)

    score = models.IntegerField()
    damage_deal = models.IntegerField()
    damage_receive = models.IntegerField()

    status = models.CharField(max_length=20)

    is_mvp = models.BooleanField(default=False)

    boss = models.JSONField()
    boss_count = models.IntegerField()

    reduction_percent = models.FloatField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "boss_battle_member_snapshot"
        indexes = [
            models.Index(fields=["project_id"]),
            models.Index(fields=["project_id", "-score"]),
        ]