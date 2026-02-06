from rest_framework import serializers

from api.models import ProjectMember, Report, Task, UserReport


class ProjectMemberBriefSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    user_id = serializers.UUIDField(source="user.user_id", read_only=True)

    class Meta:
        model = ProjectMember
        fields = [
            "project_member_id",
            "user_id",
            "username",
            "hp",
            "max_hp",
            "score",
            "status",
        ]


class TaskBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "task_id",
            "task_name",
            "description",
            "status",
            "priority",
            "deadline",
            "created_at",
            "completed_at",
        ]


class ReportResponseSerializer(serializers.ModelSerializer):
    task = TaskBriefSerializer(read_only=True)
    reporter = ProjectMemberBriefSerializer(read_only=True)

    class Meta:
        model = Report
        fields = [
            "report_id",
            "task",
            "reporter",
            "description",
            "sentiment_score",
            "created_at",
        ]


class UserReportResponseSerializer(serializers.ModelSerializer):
    report = ReportResponseSerializer(read_only=True)
    reviewer = ProjectMemberBriefSerializer(read_only=True)
    receiver = ProjectMemberBriefSerializer(read_only=True)

    class Meta:
        model = UserReport
        fields = [
            "id",
            "report",
            "reviewer",
            "receiver",
        ]


