from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api.models.Project import Project as ProjectModel
from api.services.game_service import GameService


class GameServiceTest(SimpleTestCase):
    def test_get_project_boss_raises_when_project_missing(self):
        with patch.object(ProjectModel.objects, "get", side_effect=ProjectModel.DoesNotExist):
            with self.assertRaises(ValueError):
                GameService().get_project_boss("00000000-0000-0000-0000-000000000000")

    def test_require_access_raises_when_denied(self):
        domain = MagicMock()
        domain.check_access.return_value = False
        with self.assertRaises(PermissionError):
            GameService()._require_access(domain, MagicMock())

    def test_require_access_noop_when_user_none(self):
        domain = MagicMock()
        GameService()._require_access(domain, None)
        domain.check_access.assert_not_called()

    @patch("api.services.game_service.Boss.objects")
    def test_get_all_bosses(self, mock_boss):
        mock_boss.all.return_value = [MagicMock()]
        self.assertEqual(len(GameService().get_all_bosses()), 1)

    @patch("api.services.game_service.ProjectDomain")
    @patch("api.services.game_service.ProjectModel.objects")
    def test_get_boss_status(self, mock_objects, mock_dom_cls):
        boss = MagicMock()
        boss.project_boss.project_boss_id = "pb"
        boss.boss = MagicMock(boss_id="b1")
        boss.name = "n"
        boss.image = "i"
        boss.hp = 1
        boss.max_hp = 2
        boss.status = "Alive"
        boss.phase = 1
        boss.updated_at = None
        domain = MagicMock()
        domain.game.boss = boss
        mock_dom_cls.return_value = domain
        mock_objects.get.return_value = MagicMock(project_id="p1")
        out = GameService().get_boss_status("00000000-0000-0000-0000-000000000001")
        self.assertEqual(out["hp"], 1)
