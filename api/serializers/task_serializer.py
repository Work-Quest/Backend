from rest_framework import serializers
from api.models.Task import Task

class TaskResponseSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    assignee_ids = serializers.SerializerMethodField()
    assignee_names = serializers.SerializerMethodField()
    class Meta:
        model = Task
        fields = [
            # model fields
            "task_id",
            "project",
            "priority",
            "task_name",
            "description",
            "status",
            "deadline",
            "created_at",
            "completed_at",
            # computed fields
            "project_name",
            "assignee_ids",
            "assignee_names",
        ]

    def get_assignee_ids(self, obj: Task):
        # `assigned_members` is the UserTask related_name on UserTask.task
        try:
            return [str(ut.project_member_id) for ut in obj.assigned_members.all()]
        except Exception:
            return []

    def get_assignee_names(self, obj: Task):
        # Use BusinessUser.username (not Django auth_user username) for consistency with other APIs.
        try:
            names = []
            for ut in obj.assigned_members.all():
                bu = getattr(ut.project_member, "user", None)
                if bu is None:
                    continue
                username = getattr(bu, "username", None)
                if username:
                    names.append(str(username))
            return names
        except Exception:
            return []

class TaskRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        exclude = ('project',) 

   