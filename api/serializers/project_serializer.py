from rest_framework import serializers
from api.models.Project import Project
from api.models.ProjectMember import ProjectMember

class ProjectSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.auth_user.username', read_only=True)

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
        ]
        read_only_fields = ["owner", "owner_username", "created_at", "total_tasks", "completed_tasks"]

class ProjectMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectMember
        fields = '__all__'

