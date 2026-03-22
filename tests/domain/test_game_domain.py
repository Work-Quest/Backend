import uuid
from datetime import datetime, timedelta, timezone as dt_tz
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api.domains.boss import Boss as BossDomain
from api.domains.game import Game
from api.domains.project_member import ProjectMember
from api.domains.task import Task as TaskDomain

PID = str(uuid.uuid4())


class GameDomainTest(SimpleTestCase):
    def _player(self, mid="m1", **kwargs):
        defaults = dict(
            hp=100,
            max_hp=100,
            score=0,
            status="Alive",
            project_member_id=mid,
            save=lambda **_: None,
            user=SimpleNamespace(username="u", user_id="uid1", name="N"),
            project=MagicMock(),
        )
        defaults.update(kwargs)
        return ProjectMember(SimpleNamespace(**defaults))

    def _pd(self, player, task_models):
        pd = MagicMock()
        pd.project = SimpleNamespace(project_id=PID)
        pd.TaskManagement = MagicMock()
        pd.TaskManagement.tasks = task_models
        pd.project_member_management = MagicMock()
        pd.project_member_management.members = []
        pd.project_member_management.get_member = lambda mid: player if mid == player.project_member_id else None
        return pd

    def test_player_revive_restores_alive_state(self):
        member_model = SimpleNamespace(
            hp=0,
            max_hp=100,
            score=100,
            status="Dead",
            project_member_id="m1",
            save=lambda **_: None,
        )
        player = ProjectMember(member_model)

        pd = MagicMock()
        pd.project = SimpleNamespace(project_id=PID)
        pd.TaskManagement = MagicMock()
        pd.project_member_management = MagicMock()
        pd.project_member_management.members = []
        pd.project_member_management.get_member = lambda mid: player if mid == "m1" else None

        with patch("api.domains.game.TaskLog.write"):
            game = Game(pd)
            result = game.player_revive("m1")

        self.assertEqual(result["status"], "Alive")
        self.assertEqual(player.status, "Alive")
        self.assertEqual(result["score_after"], 50)

    def test_player_revive_raises_when_alive(self):
        p = self._player(status="Alive")
        pd = self._pd(p, [])
        game = Game(pd)
        with self.assertRaises(ValueError):
            game.player_revive("m1")

    def test_boss_property_none_when_no_project_boss(self):
        pd = self._pd(self._player(), [])
        with patch("api.domains.game.ProjectBoss.objects") as pb:
            pb.filter.return_value.order_by.return_value.first.return_value = None
            game = Game(pd)
            self.assertIsNone(game.boss)

    def test_boss_property_caches_boss_domain(self):
        pd = self._pd(self._player(), [])
        pb_row = MagicMock()
        with patch("api.domains.game.ProjectBoss.objects") as pb, patch(
            "api.domains.game.BossDomain"
        ) as BD:
            pb.filter.return_value.order_by.return_value.first.return_value = pb_row
            BD.return_value = inst = MagicMock()
            game = Game(pd)
            self.assertIs(game.boss, inst)
            self.assertIs(game.boss, inst)
            self.assertEqual(BD.call_count, 1)

    def test_player_attack_happy_path(self):
        p = self._player(mid="m1", score=10)
        created = datetime(2025, 1, 1, 12, 0, tzinfo=dt_tz.utc)
        deadline = created + timedelta(days=1)
        tmodel = SimpleNamespace(
            task_id="t1",
            priority=2,
            status="done",
            deadline=deadline,
            created_at=created,
            project=SimpleNamespace(project_id=PID),
            save=lambda **_: None,
        )
        task = TaskDomain(tmodel)
        pd = self._pd(p, [task])

        boss_inner = SimpleNamespace(
            hp=500_000,
            max_hp=500_000,
            phase=1,
            status="Alive",
            updated_at=deadline,
            boss=SimpleNamespace(boss_type="normal"),
            project_boss_id="pb",
            save=lambda **_: None,
        )
        now = created + timedelta(hours=12)

        with patch("api.domains.game.TaskLog.write"), patch(
            "api.domains.project_member.UserEffect.objects.filter", return_value=[]
        ), patch("api.domains.game.timezone.now", return_value=now):
            game = Game(pd)
            game._boss = BossDomain(boss_inner)
            out = game.player_attack("m1", task)

        self.assertEqual(out["player_id"], "m1")
        self.assertLess(out["boss_hp"], 500_000)

    def test_player_attack_errors(self):
        p = self._player()
        tmodel = SimpleNamespace(
            task_id="t1",
            priority=1,
            status="done",
            deadline=datetime.now(dt_tz.utc),
            created_at=datetime.now(dt_tz.utc) - timedelta(hours=1),
            project=SimpleNamespace(project_id=PID),
            save=lambda **_: None,
        )
        task = TaskDomain(tmodel)
        pd = self._pd(p, [task])
        game = Game(pd)
        game._boss = BossDomain(
            SimpleNamespace(
                hp=10,
                max_hp=10,
                phase=1,
                status="Alive",
                updated_at=datetime.now(dt_tz.utc),
                boss=SimpleNamespace(boss_type="normal"),
                project_boss_id="pb",
                save=lambda **_: None,
            )
        )
        with self.assertRaises(ValueError):
            game.player_attack("missing", task)
        dead = self._player(mid="m2", status="Dead")
        pd2 = self._pd(dead, [task])
        pd2.project_member_management.get_member = lambda mid: dead if mid == "m2" else None
        g2 = Game(pd2)
        g2._boss = game._boss
        with self.assertRaises(ValueError):
            g2.player_attack("m2", task)

    def test_boss_attack_raises_when_task_completed(self):
        alive = self._player(mid="m1")
        boss_inner = SimpleNamespace(
            hp=10,
            max_hp=10,
            phase=1,
            status="Alive",
            updated_at=datetime.now(dt_tz.utc),
            boss=SimpleNamespace(boss_type="normal"),
            project_boss_id="pb",
            save=lambda **_: None,
        )
        pd = self._pd(alive, [])
        tmodel = SimpleNamespace(task_id="t2", priority=2, status="done", save=lambda **_: None)
        task = TaskDomain(tmodel)

        with patch.object(TaskDomain, "get_assigned_members", return_value=[alive]), patch.object(
            TaskDomain, "is_completed", return_value=True
        ):
            game = Game(pd)
            game._boss = BossDomain(boss_inner)
            with self.assertRaises(ValueError):
                game.boss_attack(task)

    def test_boss_attack_success(self):
        alive = self._player(mid="m1")
        boss_inner = SimpleNamespace(
            hp=10,
            max_hp=10,
            phase=1,
            status="Alive",
            updated_at=datetime.now(dt_tz.utc),
            boss=SimpleNamespace(boss_type="normal"),
            project_boss_id="pb",
            save=lambda **_: None,
        )
        pd = self._pd(alive, [])
        tmodel = SimpleNamespace(task_id="t2", priority=2, status="open", save=lambda **_: None)
        task = TaskDomain(tmodel)

        with patch.object(TaskDomain, "get_assigned_members", return_value=[alive]), patch.object(
            TaskDomain, "is_completed", return_value=False
        ), patch("api.domains.game.TaskLog.write"), patch(
            "api.domains.project_member.UserEffect.objects.filter", return_value=[]
        ):
            game = Game(pd)
            game._boss = BossDomain(boss_inner)
            out = game.boss_attack(task)
            self.assertEqual(out["task_id"], "t2")

    def test_player_heal(self):
        healer = self._player(mid="h1")
        target = self._player(mid="t1", hp=10, max_hp=100)

        def gm(mid):
            return healer if mid == "h1" else target if mid == "t1" else None

        pd = MagicMock()
        pd.project = SimpleNamespace(project_id=PID)
        pd.TaskManagement = MagicMock()
        pd.TaskManagement.get_task = MagicMock(return_value=None)
        pd.project_member_management = MagicMock()
        pd.project_member_management.get_member = gm

        with patch("api.domains.game.TaskLog.write"):
            game = Game(pd)
            out = game.player_heal("h1", "t1", 50)

        self.assertEqual(out["player_id"], "t1")
        self.assertGreater(out["hp"], 10)
