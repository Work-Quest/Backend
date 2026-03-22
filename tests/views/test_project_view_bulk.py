from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from tests.drf_helpers import attach_authenticated_user

from api.models import BusinessUser
from api.views.project_view import (
    accept_invite,
    batch_delete_projects,
    batch_invite,
    check_project_access,
    close_project,
    deadline_continue,
    edit_project,
    get_all_project_members,
    get_dashboard,
    get_estimate_finish_time,
    get_global_leaderboard,
    get_project_end_summary,
    get_projects,
    join_project,
    leave_project,
)


class ProjectViewBulkTest(SimpleTestCase):
    def _req(self, method, path, data=None, **kwargs):
        factory = APIRequestFactory()
        if method == "get":
            r = factory.get(path, **kwargs)
        elif method == "post":
            r = factory.post(path, data or {}, format="json", **kwargs)
        else:
            r = factory.patch(path, data or {}, format="json", **kwargs)
        attach_authenticated_user(r, username="owner", pk=1)
        return r

    @patch("api.views.project_view.CacheService")
    @patch("api.views.project_view.ProjectService")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_batch_delete_invalid_ids(self, mock_bu, _ps, _cache):
        mock_bu.return_value = MagicMock(user_id=1)
        req = self._req("post", "/bd", {})
        resp = batch_delete_projects(req)
        self.assertEqual(resp.status_code, 400)

    @patch("api.views.project_view.CacheService")
    @patch("api.views.project_view.ProjectService")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_batch_delete_runs(self, mock_bu, mock_ps, _cache):
        mock_bu.return_value = MagicMock(user_id=1)
        mock_ps.return_value.delete_project.return_value = None
        req = self._req("post", "/bd", {"project_ids": ["a", "b"]})
        resp = batch_delete_projects(req)
        self.assertEqual(resp.status_code, 200)

    @patch("api.views.project_view.ProjectSerializer")
    @patch("api.views.project_view.CacheService")
    @patch("api.views.project_view.ProjectService")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_get_projects_cache_miss(self, mock_bu, mock_ps, mock_cache_cls, mock_ser_cls):
        bu = MagicMock(user_id=9)
        mock_bu.return_value = bu
        d = MagicMock()
        d.project = MagicMock()
        mock_ps.return_value.get_projects.return_value = [d]
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_cache_cls.return_value = mock_cache
        ser = MagicMock()
        ser.data = [{"id": 1}]
        mock_ser_cls.return_value = ser
        req = self._req("get", "/gp")
        resp = get_projects(req)
        self.assertEqual(resp.status_code, 200)
        mock_cache.set.assert_called()

    @patch("api.views.project_view.CacheService")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_get_projects_cache_hit(self, mock_bu, mock_cache_cls):
        mock_bu.return_value = MagicMock(user_id=9)
        mock_cache = MagicMock()
        mock_cache.get.return_value = [{"cached": True}]
        mock_cache_cls.return_value = mock_cache
        req = self._req("get", "/gp")
        resp = get_projects(req)
        self.assertEqual(resp.status_code, 200)

    @patch("api.views.project_view.CacheService")
    @patch("api.views.project_view.ProjectService")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_join_project_not_found_message(self, mock_bu, mock_ps, _cache):
        mock_bu.return_value = MagicMock(user_id=1)
        mock_ps.return_value.join_project.return_value = {
            "message": "Project not found",
            "member": None,
        }
        req = self._req(
            "post", "/j", {"project_id": "00000000-0000-0000-0000-000000000001"}
        )
        resp = join_project(req)
        self.assertEqual(resp.status_code, 404)

    @patch("api.views.project_view.ProjectMemberSerializer")
    @patch("api.views.project_view.CacheService")
    @patch("api.views.project_view.ProjectService")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_join_project_success(self, mock_bu, mock_ps, _cache, mock_pms):
        mock_bu.return_value = MagicMock(user_id=1)
        member = MagicMock()
        mock_ps.return_value.join_project.return_value = {"member": member}
        mock_pms.return_value.data = {"id": "m"}
        req = self._req(
            "post", "/j", {"project_id": "00000000-0000-0000-0000-000000000001"}
        )
        resp = join_project(req)
        self.assertEqual(resp.status_code, 201)

    @patch("api.views.project_view.CacheService")
    @patch("api.views.project_view.ProjectService")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_leave_project_fail(self, mock_bu, mock_ps, _cache):
        mock_bu.return_value = MagicMock(user_id=1)
        mock_ps.return_value.leave_project.return_value = False
        req = self._req(
            "post", "/lv", {"project_id": "00000000-0000-0000-0000-000000000001"}
        )
        resp = leave_project(req)
        self.assertEqual(resp.status_code, 400)

    @patch("api.views.project_view.CacheService")
    @patch("api.views.project_view.ProjectService")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_leave_project_ok(self, mock_bu, mock_ps, _cache):
        mock_bu.return_value = MagicMock(user_id=1)
        mock_ps.return_value.leave_project.return_value = True
        req = self._req(
            "post", "/lv", {"project_id": "00000000-0000-0000-0000-000000000001"}
        )
        resp = leave_project(req)
        self.assertEqual(resp.status_code, 200)

    @patch("api.views.project_view.BusinessUser.objects.get")
    @patch("api.views.project_view.ProjectModel.objects.get")
    def test_batch_invite_not_owner(self, mock_proj_get, mock_bu_get):
        owner = MagicMock()
        other = MagicMock()
        mock_bu_get.return_value = other
        mock_proj_get.return_value = MagicMock(owner=owner)
        req = self._req(
            "post", "/inv", {"user_ids": ["u1"]}, HTTP_HOST="localhost"
        )
        resp = batch_invite(req, project_id="pid")
        self.assertEqual(resp.status_code, 403)

    @patch("api.views.project_view.JoinService")
    @patch("api.views.project_view.BusinessUser.objects.get")
    @patch("api.views.project_view.ProjectModel.objects.get")
    def test_batch_invite_success(self, mock_proj_get, mock_bu_get, mock_join):
        owner = MagicMock()
        owner.user_id = "owner"
        invited = MagicMock()
        invited.user_id = "u1"
        invited.email = "a@b.com"
        mock_bu_get.side_effect = [owner, invited]
        mock_proj_get.return_value = MagicMock(owner=owner)
        mock_join.return_value.invite_players.return_value = {"created": []}
        req = self._req(
            "post", "/inv", {"user_ids": ["u1"], "expires_in_days": "x"},
            HTTP_HOST="localhost",
        )
        with patch.dict("os.environ", {"DB_ENV": "dev"}, clear=False):
            resp = batch_invite(req, project_id="pid")
        self.assertEqual(resp.status_code, 201)

    @patch("api.views.project_view.CacheService")
    @patch("api.views.project_view.JoinService")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_accept_invite_invalid_token_404(self, mock_bu, mock_join, _cache):
        mock_bu.return_value = MagicMock(user_id=1)
        mock_join.return_value.accept_invite.return_value = {
            "error": "Invalid invite token"
        }
        req = self._req("post", "/acc", {"token": "t"})
        resp = accept_invite(req)
        self.assertEqual(resp.status_code, 404)

    @patch("api.views.project_view.ProjectSerializer")
    @patch("api.views.project_view.CacheService")
    @patch("api.views.project_view.ProjectService")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_close_project(self, mock_bu, mock_ps, _cache, mock_ser):
        mock_bu.return_value = MagicMock(user_id=1)
        dom = MagicMock()
        dom.project = MagicMock()
        mock_ps.return_value.close_project.return_value = dom
        mock_ser.return_value.data = {"status": "closed"}
        req = self._req(
            "post", "/cl", {"project_id": "00000000-0000-0000-0000-000000000001"}
        )
        resp = close_project(req)
        self.assertEqual(resp.status_code, 200)

    @patch("api.views.project_view.ProjectService")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_check_access_not_found(self, mock_bu, mock_ps):
        mock_bu.return_value = MagicMock()
        mock_ps.return_value.check_project_access.return_value = None
        req = self._req("get", "/ca")
        resp = check_project_access(req, project_id="pid")
        self.assertEqual(resp.status_code, 404)

    @patch("api.views.project_view.ProjectService")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_check_access_yes_no(self, mock_bu, mock_ps):
        mock_bu.return_value = MagicMock()
        mock_ps.return_value.check_project_access.side_effect = [True, False]
        req = self._req("get", "/ca1")
        self.assertEqual(check_project_access(req, "p1").status_code, 200)
        req2 = self._req("get", "/ca2")
        self.assertEqual(check_project_access(req2, "p2").status_code, 403)

    @patch("api.views.project_view.CacheService")
    @patch("api.views.project_view.ProjectService")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_get_all_project_members(self, mock_bu, mock_ps, mock_cache_cls):
        mock_bu.return_value = MagicMock()
        m = MagicMock()
        m.project_member_id = "1"
        m.user = MagicMock(name="N", username="u", selected_character_id=1, bg_color_id=1)
        m.hp = 10
        m.status = "Alive"
        mock_ps.return_value.get_all_project_members.return_value = [m]
        mock_cache = MagicMock()
        mock_cache.read_through.side_effect = lambda **kw: kw["loader"]()
        mock_cache.keys.project_members.return_value = "k"
        mock_cache_cls.return_value = mock_cache
        req = self._req("get", "/mem")
        resp = get_all_project_members(req, project_id="pid")
        self.assertEqual(resp.status_code, 200)

    @patch("api.views.project_view.CacheService")
    @patch("api.views.project_view.timezone")
    @patch("api.models.ProjectMember.ProjectMember.objects.filter")
    @patch("api.views.project_view.ProjectModel.objects.get")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_deadline_continue_success(
        self, mock_bu, mock_pget, mock_pm_filter, mock_tz, _cache
    ):
        mock_bu.return_value = MagicMock(user_id=1)
        past = timezone.now() - timedelta(days=1)
        proj = MagicMock()
        proj.deadline = past
        proj.deadline_decision = None
        proj.deadline_decision_date = None
        proj.save = MagicMock()
        mock_pget.return_value = proj
        mock_pm_filter.return_value.exists.return_value = True
        mock_tz.now.return_value = timezone.now()
        req = self._req("post", "/dc", {}, HTTP_HOST="localhost")
        resp = deadline_continue(req, project_id="pid")
        self.assertEqual(resp.status_code, 200)

    @patch("api.views.project_view.ProjectService")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_get_project_end_summary(self, mock_bu, mock_ps):
        mock_bu.return_value = MagicMock()
        mock_ps.return_value.get_project_end_summary.return_value = {"ok": True}
        req = self._req("get", "/sum")
        resp = get_project_end_summary(req, project_id="pid")
        self.assertEqual(resp.status_code, 200)

    @patch("api.views.project_view.Task")
    @patch("api.models.ProjectMember.ProjectMember.objects.filter")
    @patch("api.views.project_view.ProjectModel.objects.get")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_get_estimate_finish_time_no_completed(
        self, mock_bu, mock_pget, mock_pm, mock_task
    ):
        mock_bu.return_value = MagicMock()
        mock_pget.return_value = MagicMock()
        mock_pm.return_value.exists.return_value = True
        qs = MagicMock()
        qs.exists.return_value = False
        mock_task.objects.filter.return_value = qs
        req = self._req("get", "/est")
        resp = get_estimate_finish_time(req, project_id="pid")
        self.assertEqual(resp.status_code, 200)

    @patch("api.views.project_view.ProjectService")
    @patch("api.models.ProjectMember.ProjectMember.objects.filter")
    @patch("api.views.project_view.ProjectModel.objects.get")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_get_dashboard_ok(self, mock_bu, mock_pget, mock_pm, mock_psvc):
        mock_bu.return_value = MagicMock()
        mock_pget.return_value = MagicMock()
        mock_pm.return_value.exists.return_value = True
        mock_psvc.return_value.get_dashboard_data.return_value = {"d": 1}
        req = self._req("get", "/dash")
        resp = get_dashboard(req, project_id="pid")
        self.assertEqual(resp.status_code, 200)

    @patch("api.views.project_view.ProjectService")
    def test_get_global_leaderboard_ok(self, mock_ps):
        mock_ps.return_value.get_global_leaderboard.return_value = []
        req = self._req("get", "/lb")
        resp = get_global_leaderboard(req)
        self.assertEqual(resp.status_code, 200)

    @patch("api.views.project_view.ProjectService")
    def test_get_global_leaderboard_error(self, mock_ps):
        mock_ps.return_value.get_global_leaderboard.side_effect = RuntimeError("x")
        req = self._req("get", "/lb")
        resp = get_global_leaderboard(req)
        self.assertEqual(resp.status_code, 400)

    @patch("api.views.project_view.ProjectSerializer")
    @patch("api.views.project_view.CacheService")
    @patch("api.views.project_view.ProjectService")
    @patch("api.views.project_view.BusinessUser.objects.get")
    def test_edit_project_ok(self, mock_bu, mock_ps, _cache, mock_ser):
        mock_bu.return_value = MagicMock()
        dom = MagicMock()
        dom.project = MagicMock()
        mock_ps.return_value.edit_project.return_value = dom
        mock_ser.return_value.data = {"id": 1}
        factory = APIRequestFactory()
        req = factory.post(
            "/e",
            {"deadline": "2027-01-01T00:00:00Z", "project_name": "P"},
            format="json",
        )
        attach_authenticated_user(req, username="owner", pk=1)
        resp = edit_project(req, project_id="pid")
        self.assertEqual(resp.status_code, 200)
