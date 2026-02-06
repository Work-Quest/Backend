from rest_framework import serializers
from api.models.Boss import Boss
from api.models.ProjectBoss import ProjectBoss

class BossSerializer(serializers.ModelSerializer):
    class Meta:
        model = Boss
        fields = [
            "boss_id",
            "boss_name",
            "boss_image",
        ]

class ProjectBossSerializer(serializers.ModelSerializer):
    boss_name = serializers.CharField(source='boss.boss_name', read_only=True)
    boss_image = serializers.JSONField(source='boss.boss_image', read_only=True)

    class Meta:
        model = ProjectBoss
        fields = [
            "project_boss_id",
            "project",
            "boss",
            "boss_name",
            "boss_image",
            "hp",
            "max_hp",
            "status",
        ]
        read_only_fields = ["project", "boss_name", "boss_image"]










