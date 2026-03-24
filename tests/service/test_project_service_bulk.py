import uuid
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api.services.project_service import ProjectService


class ProjectServiceBulkTest(SimpleTestCase):
    @patch("api.services.project_service.ProjectDomain")
    @patch("api.services.project_service.ProjectModel.objects")
    def test_close_project(self, mock_proj, mock_dom):
        mock_proj.get.return_value = MagicMock()
        mock_dom.return_value = MagicMock()
        domain = ProjectService().close_project("pid", user=MagicMock())
        self.assertIsNotNone(domain)

    @patch("api.services.project_service.ProjectDomain")
    @patch("api.services.project_service.ProjectModel.objects")
    def test_check_project_access(self, mock_proj, mock_dom):
        mock_proj.get.return_value = MagicMock()
        mock_dom.return_value.check_access.return_value = True
        self.assertTrue(ProjectService().check_project_access("pid", MagicMock()))

    @patch("api.services.project_service.ProjectDomain")
    @patch("api.services.project_service.ProjectModel.objects")
    def test_get_all_project_members(self, mock_proj, mock_dom):
        mock_proj.get.return_value = MagicMock()
        mock_dom.return_value._project_member_management.members = [MagicMock()]
        mems = ProjectService().get_all_project_members("pid")
        self.assertEqual(len(mems), 1)

    @patch("api.services.project_service.transaction.atomic")
    @patch("api.services.project_service.ProjectEndSummary.objects")
    @patch("api.services.project_service.TaskLog.objects")
    @patch("api.services.project_service.ProjectBoss.objects")
    @patch("api.services.project_service.ProjectMember.objects")
    @patch("api.services.project_service.ProjectDomain")
    @patch("api.services.project_service.ProjectModel.objects")
    def test_get_project_end_summary_computes_when_missing(
        self,
        mock_proj,
        mock_dom,
        mock_pm,
        mock_boss,
        mock_log,
        mock_summary,
        mock_tx,
    ):
        mock_tx.return_value.__enter__ = lambda *a: None
        mock_tx.return_value.__exit__ = lambda *a: None
        proj = MagicMock()
        proj.deadline = None
        proj.deadline_decision = None
        mock_proj.get.return_value = proj
        mock_pm.filter.return_value.exists.return_value = True
        existing_qs = MagicMock()
        existing_qs.exists.return_value = False
        mock_summary.filter.return_value = existing_qs
        member = MagicMock()
        member.project_member_id = "mid"
        member.user.user_id = "uid"
        member.user.name = "N"
        member.user.username = "u"
        member.score = 10
        member.status = "Alive"
        domain = MagicMock()
        domain._project_member_management.members = [member]
        mock_dom.return_value = domain
        mock_log.filter.return_value.values_list.return_value = [{"damage": 1}]
        boss_qs = MagicMock()
        boss_qs.__iter__ = lambda self: iter([])
        boss_qs.count.return_value = 0
        mock_boss.filter.return_value = boss_qs
        mock_summary.create = MagicMock()
        out = ProjectService().get_project_end_summary(MagicMock(), "pid")
        self.assertIn("users", out)

    @patch("api.services.project_service.ProjectEndSummary.objects")
    @patch("api.services.project_service.ProjectMember.objects")
    @patch("api.services.project_service.ProjectModel.objects")
    def test_get_project_end_summary_cached(self, mock_proj, mock_pm, mock_sum):
        mock_proj.get.return_value = MagicMock()
        mock_pm.filter.return_value.exists.return_value = True
        qs = MagicMock()
        qs.exists.return_value = True
        qs.first.return_value = MagicMock(
            boss_count=1,
            boss=[],
            reduction_percent=0,
        )
        qs.order_by.return_value.values.return_value = []
        mock_sum.filter.return_value = qs
        out = ProjectService().get_project_end_summary(MagicMock(), "pid")
        self.assertIn("users", out)

    @patch("api.models.BusinessUser.BusinessUser.objects")
    @patch("api.services.project_service.ProjectEndSummary.objects")
    def test_get_global_leaderboard_builds_rows(self, mock_pes, mock_bu):
        mock_pes.values.return_value.annotate.return_value = [
            {"user_id": "u1", "max_score": 100}
        ]
        prof = MagicMock()
        prof.user_id = "u1"
        prof.selected_character_id = 2
        prof.bg_color_id = 3
        mock_bu.all.return_value = [prof]
        rec = MagicMock()
        rec.user_id = "u1"
        rec.score = 100
        rec.name = "n"
        rec.username = "u"
        rec.damage_deal = 1
        rec.damage_receive = 2
        rec.status = "Alive"
        mock_pes.order_by.return_value = [rec]
        out = ProjectService().get_global_leaderboard()
        self.assertEqual(len(out), 1)

    def test_get_user_finished_projects_empty_user(self):
        self.assertEqual(ProjectService().get_user_finished_projects(), [])

    @patch("api.services.project_service.ProjectEndSummary.objects")
    @patch("api.services.project_service.ProjectModel.objects")
    def test_get_user_finished_projects_with_user(self, mock_proj, mock_pes):
        u = MagicMock()
        u.user_id = "uid"

        summary_row = MagicMock()
        summary_row.order_by.return_value.first.return_value = MagicMock(
            score=5, boss_count=1
        )

        list_qs = MagicMock()
        list_qs.values.return_value.annotate.return_value.order_by.return_value = [
            {"project_id": "p1"}
        ]

        def _filter(*a, **kw):
            if kw.get("project_id"):
                return summary_row
            return list_qs

        mock_pes.filter.side_effect = _filter
        mock_proj.get.return_value = MagicMock(project_name="Pn")
        out = ProjectService().get_user_finished_projects(user=u)
        self.assertEqual(len(out), 1)

    @patch("api.services.project_service.ProjectMember.objects")
    @patch("api.services.project_service.ProjectEndSummary.objects")
    def test_get_user_profile_stats_defaults(self, mock_pes, mock_pm):
        mock_pes.filter.return_value.exists.return_value = False
        out = ProjectService().get_user_profile_stats(user=MagicMock())
        self.assertEqual(out["highest_score"], 0)

    @patch("api.services.project_service.ProjectMember.objects")
    @patch("api.services.project_service.ProjectEndSummary.objects")
    def test_get_user_profile_stats_with_data(self, mock_pes, mock_pm):
        mock_pes.filter.return_value.exists.return_value = True
        mock_pes.filter.return_value.aggregate.side_effect = [
            {"max_score": 50},
            {"total": 3},
        ]
        mock_pm.filter.return_value.count.return_value = 2
        out = ProjectService().get_user_profile_stats(user=MagicMock())
        self.assertEqual(out["highest_score"], 50)

    @patch("api.services.project_service.ProjectEndSummary.objects")
    def test_get_user_defeated_bosses_parses_boss_json(self, mock_pes):
        s = MagicMock()
        s.boss = [{"id": "b1", "name": "B", "type": "Normal"}]
        mock_pes.filter.return_value = [s]
        out = ProjectService().get_user_defeated_bosses(user=MagicMock())
        self.assertEqual(len(out), 1)
