from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api.services.achievement_service import (
    compute_achievement_ids,
    get_overall_achievement_ids_for_user,
)


class AchievementServiceTest(SimpleTestCase):
    @patch("api.services.achievement_service.UserFeedback.objects")
    @patch("api.services.achievement_service.ProjectMember.objects")
    def test_get_overall_returns_empty_when_no_memberships(self, mock_pm, mock_uf):
        mock_pm.filter.return_value.values_list.return_value = []
        mock_uf.filter.return_value.select_related.return_value = []

        out = get_overall_achievement_ids_for_user(MagicMock())
        self.assertEqual(out, [])

    @patch("api.services.achievement_service.ProjectMember.objects")
    @patch("api.services.achievement_service._member_game_context")
    @patch("api.services.achievement_service._compute_task_stats_for_member_project")
    def test_compute_includes_zombie_achievement(self, mock_stats, mock_ctx, mock_pm):
        mock_stats.return_value = {
            "total_assigned": 4,
            "completed": 4,
            "late": 0,
            "near_deadline": 1,
        }
        mock_ctx.return_value = {
            "killed_by_boss": True,
            "revived": True,
            "killed_boss": False,
            "hp": 100,
            "max_hp": 100,
            "score": 10,
            "member": MagicMock(status="Alive"),
        }
        fb = MagicMock()
        fb.overall_quality_score = 80
        fb.team_work = 80
        fb.diligence = 75
        proj = MagicMock()
        proj.members.count.return_value = 2
        fb.project = proj
        qs = MagicMock()
        qs.order_by.return_value.values_list.return_value.first.return_value = 10
        mock_pm.filter.return_value = qs
        ids = compute_achievement_ids(fb)
        self.assertIn("01", ids)
