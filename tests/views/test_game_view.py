from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from tests.drf_helpers import attach_authenticated_user

from api.models import BusinessUser
from api.models.ProjectMember import ProjectMember
from api.views import game_view as gv


def _boss_domain(boss_linked=True):
    d = MagicMock()
    d.project_boss.project_boss_id = "pb1"
    d.project_boss.project.project_id = "p1"
    if boss_linked:
        d.boss = MagicMock(boss_id="b1", boss_type="Normal")
        d.name = "Dragon"
        d.image = "i.png"
    else:
        d.boss = None
        d.name = None
        d.image = None
    d.hp = 50
    d.max_hp = 100
    d.status = "Alive"
    d.phase = 1
    return d


class GameViewTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch("api.views.game_view.GameService")
    def test_get_project_boss_returns_404_when_service_raises_value_error(self, mock_svc_cls):
        mock_svc_cls.return_value.get_project_boss.side_effect = ValueError("Boss not initialized")
        request = self.factory.get("/game/boss/")
        attach_authenticated_user(request)
        response = gv.get_project_boss(request, project_id="pid")
        self.assertEqual(response.status_code, 404)

    @patch("api.views.game_view.GameService")
    def test_get_project_boss_success(self, mock_svc_cls):
        mock_svc_cls.return_value.get_project_boss.return_value = _boss_domain()
        request = self.factory.get("/game/boss/")
        attach_authenticated_user(request)
        response = gv.get_project_boss(request, project_id="pid")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["hp"], 50)

    @patch("api.views.game_view.GameService")
    def test_get_project_boss_400_on_unexpected(self, mock_svc_cls):
        mock_svc_cls.return_value.get_project_boss.side_effect = RuntimeError("x")
        request = self.factory.get("/x")
        attach_authenticated_user(request)
        response = gv.get_project_boss(request, project_id="pid")
        self.assertEqual(response.status_code, 400)

    @patch("api.views.game_view.BossSerializer")
    @patch("api.views.game_view.GameService")
    def test_get_all_bosses(self, mock_gs, mock_ser):
        mock_gs.return_value.get_all_bosses.return_value = [MagicMock()]
        mock_ser.return_value.data = [{"id": 1}]
        request = self.factory.get("/bosses/")
        attach_authenticated_user(request)
        response = gv.get_all_bosses(request)
        self.assertEqual(response.status_code, 200)

    @patch("api.views.game_view.CacheService")
    @patch("api.views.game_view.GameService")
    def test_setup_project_boss_success(self, mock_gs, mock_cache):
        mock_gs.return_value.setup_boss_for_project.return_value = _boss_domain()
        request = self.factory.post("/setup/", {}, format="json")
        attach_authenticated_user(request)
        response = gv.setup_project_boss(request, project_id="pid")
        self.assertEqual(response.status_code, 200)
        self.assertIn("boss", response.data)

    @patch("api.views.game_view.GameService")
    def test_setup_project_boss_404(self, mock_gs):
        mock_gs.return_value.setup_boss_for_project.side_effect = ValueError("nope")
        request = self.factory.post("/setup/", {}, format="json")
        attach_authenticated_user(request)
        self.assertEqual(gv.setup_project_boss(request, "pid").status_code, 404)

    def test_player_attack_requires_task_id(self):
        request = self.factory.post("/atk/", {}, format="json")
        attach_authenticated_user(request)
        self.assertEqual(gv.player_attack(request, "pid").status_code, 400)

    @patch("api.views.game_view.CacheService")
    @patch("api.views.game_view.GameService")
    def test_player_attack_success(self, mock_gs, _cache):
        mock_gs.return_value.player_attack.return_value = {"ok": True}
        request = self.factory.post("/atk/", {"task_id": "t1"}, format="json")
        attach_authenticated_user(request)
        r = gv.player_attack(request, "pid")
        self.assertEqual(r.status_code, 200)

    @patch("api.views.game_view.GameService")
    def test_player_attack_permission(self, mock_gs):
        mock_gs.return_value.player_attack.side_effect = PermissionError("no")
        request = self.factory.post("/atk/", {"task_id": "t1"}, format="json")
        attach_authenticated_user(request)
        self.assertEqual(gv.player_attack(request, "pid").status_code, 403)

    @patch("api.views.game_view.GameService")
    def test_player_attack_value_error(self, mock_gs):
        mock_gs.return_value.player_attack.side_effect = ValueError("bad")
        request = self.factory.post("/atk/", {"task_id": "t1"}, format="json")
        attach_authenticated_user(request)
        self.assertEqual(gv.player_attack(request, "pid").status_code, 400)

    def test_boss_attack_requires_task_id(self):
        request = self.factory.post("/b/", {}, format="json")
        attach_authenticated_user(request)
        self.assertEqual(gv.boss_attack(request, "pid").status_code, 400)

    @patch("api.views.game_view.CacheService")
    @patch("api.views.game_view.GameService")
    def test_boss_attack_success(self, mock_gs, _c):
        mock_gs.return_value.boss_attack.return_value = {}
        request = self.factory.post("/b/", {"task_id": "t1"}, format="json")
        attach_authenticated_user(request)
        self.assertEqual(gv.boss_attack(request, "pid").status_code, 200)

    def test_player_heal_validation(self):
        request = self.factory.post("/h/", {}, format="json")
        attach_authenticated_user(request)
        self.assertEqual(gv.player_heal(request, "pid").status_code, 400)
        request = self.factory.post(
            "/h/", {"healer_id": "a", "player_id": "b", "heal_value": "x"}, format="json"
        )
        attach_authenticated_user(request)
        self.assertEqual(gv.player_heal(request, "pid").status_code, 400)
        request = self.factory.post(
            "/h/", {"healer_id": "a", "player_id": "b", "heal_value": 0}, format="json"
        )
        attach_authenticated_user(request)
        self.assertEqual(gv.player_heal(request, "pid").status_code, 400)

    @patch("api.views.game_view.CacheService")
    @patch("api.views.game_view.GameService")
    def test_player_heal_success(self, mock_gs, _c):
        mock_gs.return_value.player_heal.return_value = {"hp": 10}
        request = self.factory.post(
            "/h/", {"healer_id": "a", "player_id": "b", "heal_value": 5}, format="json"
        )
        attach_authenticated_user(request)
        self.assertEqual(gv.player_heal(request, "pid").status_code, 200)

    def test_player_support_requires_report_id(self):
        request = self.factory.post("/s/", {}, format="json")
        attach_authenticated_user(request)
        self.assertEqual(gv.player_support(request, "pid").status_code, 400)

    @patch("api.views.game_view.CacheService")
    @patch("api.views.game_view.GameService")
    @patch.object(BusinessUser.objects, "get")
    def test_player_support_success(self, mock_bu_get, mock_gs, _c):
        mock_bu_get.return_value = MagicMock()
        mock_gs.return_value.player_support.return_value = {"r": 1}
        request = self.factory.post("/s/", {"report_id": "r1"}, format="json")
        attach_authenticated_user(request)
        self.assertEqual(gv.player_support(request, "pid").status_code, 200)

    @patch.object(BusinessUser.objects, "get", side_effect=BusinessUser.DoesNotExist)
    def test_player_support_no_business_user(self, _mock_get):
        request = self.factory.post("/s/", {"report_id": "r1"}, format="json")
        attach_authenticated_user(request)
        self.assertEqual(gv.player_support(request, "pid").status_code, 400)

    def test_revive_requires_player_id(self):
        request = self.factory.post("/r/", {}, format="json")
        attach_authenticated_user(request)
        self.assertEqual(gv.revive(request, "pid").status_code, 400)

    @patch("api.views.game_view.CacheService")
    @patch("api.views.game_view.GameService")
    def test_revive_success(self, mock_gs, _c):
        mock_gs.return_value.revive_player.return_value = None
        request = self.factory.post("/r/", {"player_id": "m1"}, format="json")
        attach_authenticated_user(request)
        self.assertEqual(gv.revive(request, "pid").status_code, 200)

    @patch("api.views.game_view.CacheService")
    @patch("api.views.game_view.GameService")
    def test_get_boss_status_cached(self, mock_gs, mock_cache_cls):
        mock_cache = MagicMock()
        mock_cache.keys.boss_status.return_value = "k"
        mock_cache.read_through.return_value = {"s": 1}
        mock_cache_cls.return_value = mock_cache
        request = self.factory.get("/st/")
        attach_authenticated_user(request)
        r = gv.get_boss_status(request, "pid")
        self.assertEqual(r.status_code, 200)
        mock_cache.read_through.assert_called_once()

    @patch("api.views.game_view.CacheService")
    @patch("api.views.game_view.GameService")
    def test_get_user_statuses(self, mock_gs, mock_cache_cls):
        mock_cache = MagicMock()
        mock_cache.keys.user_statuses.return_value = "k"
        mock_cache.read_through.return_value = []
        mock_cache_cls.return_value = mock_cache
        request = self.factory.get("/us/")
        attach_authenticated_user(request)
        self.assertEqual(gv.get_user_statuses(request, "pid").status_code, 200)

    @patch("api.views.game_view.CacheService")
    @patch("api.views.game_view.GameService")
    def test_get_game_status(self, mock_gs, mock_cache_cls):
        mock_cache = MagicMock()
        mock_cache.keys.game_status.return_value = "k"
        mock_cache.read_through.return_value = {}
        mock_cache_cls.return_value = mock_cache
        request = self.factory.get("/gs/")
        attach_authenticated_user(request)
        self.assertEqual(gv.get_game_status(request, "pid").status_code, 200)

    @patch("api.views.game_view.CacheService")
    @patch("api.views.game_view.ProjectBossSerializer")
    @patch("api.views.game_view.GameService")
    def test_setup_special_boss(self, mock_gs, mock_pbs, _c):
        mock_model = MagicMock()
        mock_gs.return_value.setup_special_boss.return_value = mock_model
        mock_pbs.return_value.data = {"id": "x"}
        request = self.factory.post("/sp/", {}, format="json")
        attach_authenticated_user(request)
        r = gv.setup_special_boss(request, "pid")
        self.assertEqual(r.status_code, 200)

    @patch("api.views.game_view.CacheService")
    @patch("api.views.game_view.GameService")
    @patch.object(ProjectMember.objects, "get")
    @patch.object(BusinessUser.objects, "get")
    def test_get_project_member_items(self, mock_bu, mock_pm, mock_gs, mock_cache_cls):
        mock_bu.return_value = MagicMock()
        mock_pm.return_value = MagicMock(project_member_id="mid")
        mock_gs.return_value.get_project_member_items.return_value = {"items": []}
        mock_cache = MagicMock()
        mock_cache.keys.project_member_items.return_value = "k"
        mock_cache.read_through.side_effect = lambda **kw: kw["loader"]()
        mock_cache_cls.return_value = mock_cache
        request = self.factory.get("/items/")
        attach_authenticated_user(request)
        self.assertEqual(gv.get_project_member_items(request, "pid").status_code, 200)

    @patch("api.views.game_view.CacheService")
    @patch("api.views.game_view.GameService")
    @patch.object(ProjectMember.objects, "get")
    @patch.object(BusinessUser.objects, "get")
    def test_use_project_member_item(self, mock_bu, mock_pm, mock_gs, _c):
        mock_bu.return_value = MagicMock()
        mock_pm.return_value = MagicMock(project_member_id="mid")
        mock_gs.return_value.use_project_member_item.return_value = {"used": True}
        request = self.factory.post("/use/", {"item_id": "i1"}, format="json")
        attach_authenticated_user(request)
        self.assertEqual(gv.use_project_member_item(request, "pid").status_code, 200)

    def test_use_project_member_item_requires_item_id(self):
        request = self.factory.post("/use/", {}, format="json")
        attach_authenticated_user(request)
        self.assertEqual(gv.use_project_member_item(request, "pid").status_code, 400)

    @patch("api.views.game_view.CacheService")
    @patch("api.views.game_view.GameService")
    @patch.object(ProjectMember.objects, "get")
    @patch.object(BusinessUser.objects, "get")
    def test_get_project_member_status_effects(self, mock_bu, mock_pm, mock_gs, mock_cache_cls):
        mock_bu.return_value = MagicMock()
        mock_pm.return_value = MagicMock(project_member_id="mid")
        mock_gs.return_value.get_project_member_status_effects.return_value = {}
        mock_cache = MagicMock()
        mock_cache.keys.project_member_status_effects.return_value = "k"
        mock_cache.read_through.side_effect = lambda **kw: kw["loader"]()
        mock_cache_cls.return_value = mock_cache
        request = self.factory.get("/fx/")
        attach_authenticated_user(request)
        self.assertEqual(gv.get_project_member_status_effects(request, "pid").status_code, 200)

    @patch.object(ProjectMember.objects, "get", side_effect=ProjectMember.DoesNotExist)
    @patch.object(BusinessUser.objects, "get")
    def test_get_project_member_items_not_member(self, _bu, _pm):
        request = self.factory.get("/items/")
        attach_authenticated_user(request)
        self.assertEqual(gv.get_project_member_items(request, "pid").status_code, 403)
