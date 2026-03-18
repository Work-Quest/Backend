from rest_framework import serializers

from api.models.UserFeedback import UserFeedback
from api.services.achievement_service import compute_achievement_ids


class UserFeedbackSerializer(serializers.ModelSerializer):
    project_member_id = serializers.UUIDField(
        source="user.project_member_id", read_only=True
    )
    project_id = serializers.UUIDField(
        source="project.project_id", read_only=True
    )
    achievement_ids = serializers.SerializerMethodField()

    class Meta:
        model = UserFeedback
        fields = [
            "feedback_id",
            "project_member_id",
            "project_id",
            "feedback_text",
            "overall_quality_score",
            "team_work",
            "strength",
            "work_load_per_day",
            "work_speed",
            "diligence",
            "role_assigned",
            "created_at",
            "achievement_ids",
        ]
        read_only_fields = fields

    def get_achievement_ids(self, obj: UserFeedback) -> list[str]:
        return compute_achievement_ids(obj)


