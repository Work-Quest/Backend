from rest_framework import serializers
from api.models.Project import Project
from api.models.ProjectMember import ProjectMember
from api.models.ProjectBoss import ProjectBoss


class ProjectSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.auth_user.username', read_only=True)
    boss_name = serializers.SerializerMethodField()
    boss_image = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "project_id",
            "project_name",
            "status",
            "owner",
            "owner_username",
            "created_at",
            "deadline",
            "total_tasks",
            "completed_tasks",
            "boss_name",
            "boss_image",
        ]
        read_only_fields = [
            "owner",
            "owner_username",
            "created_at",
            "total_tasks",
            "completed_tasks",
            "boss_name",
            "boss_image",
        ]

    @staticmethod
    def _current_project_boss(project: Project):
        """Latest row with a linked Boss (sprite id lives on Boss.boss_image, name on Boss.boss_name)."""
        return (
            ProjectBoss.objects.filter(project=project, boss__isnull=False)
            .select_related("boss")
            .order_by("-updated_at")
            .first()
        )

    def get_boss_name(self, obj):
        pb = self._current_project_boss(obj)
        return pb.boss.boss_name if pb and pb.boss else None

    def get_boss_image(self, obj):
        pb = self._current_project_boss(obj)
        return pb.boss.boss_image if pb and pb.boss else None

class ProjectMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectMember
        fields = '__all__'

