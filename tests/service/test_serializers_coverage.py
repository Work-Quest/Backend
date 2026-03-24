
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api.serializers.feedback_serializer import UserFeedbackSerializer
from api.serializers.project_serializer import ProjectSerializer
from api.serializers.task_serializer import TaskResponseSerializer


class SerializersCoverageTest(SimpleTestCase):
    def test_task_response_assignee_methods(self):
        ut = MagicMock()
        ut.project_member_id = "mid"
        bu = MagicMock()
        bu.username = "alice"
        ut.project_member.user = bu
        mgr = MagicMock()
        mgr.all.return_value = [ut]
        task = MagicMock()
        task.assigned_members = mgr
        ser = TaskResponseSerializer()
        self.assertEqual(ser.get_assignee_ids(task), ["mid"])
        self.assertEqual(ser.get_assignee_names(task), ["alice"])

    def test_task_response_assignee_ids_exception_returns_empty(self):
        task = MagicMock()
        task.assigned_members.all.side_effect = RuntimeError("db")
        ser = TaskResponseSerializer()
        self.assertEqual(ser.get_assignee_ids(task), [])

    @patch("api.serializers.project_serializer.ProjectBoss.objects")
    def test_project_serializer_boss_fields(self, mock_pb):
        row = MagicMock()
        row.boss = MagicMock(boss_name="B", boss_image="img.png")
        mock_pb.filter.return_value.select_related.return_value.order_by.return_value.first.return_value = (
            row
        )
        proj = MagicMock()
        ser = ProjectSerializer()
        self.assertEqual(ser.get_boss_name(proj), "B")
        self.assertEqual(ser.get_boss_image(proj), "img.png")

    @patch("api.serializers.feedback_serializer.compute_achievement_ids", return_value=["01"])
    def test_user_feedback_achievement_ids(self, _mock_compute):
        ser = UserFeedbackSerializer()
        self.assertEqual(ser.get_achievement_ids(MagicMock()), ["01"])
