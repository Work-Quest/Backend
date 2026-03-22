from datetime import datetime, timezone as dt_timezone
from types import SimpleNamespace

from django.test import SimpleTestCase

from api.utils.log_payloads import project_member_snapshot, task_snapshot


class LogPayloadsTest(SimpleTestCase):
    def test_task_snapshot_none(self):
        self.assertIsNone(task_snapshot(None))

    def test_task_snapshot_without_task_id(self):
        self.assertIsNone(task_snapshot(SimpleNamespace(foo=1)))

    def test_task_snapshot_from_model_like(self):
        dt = datetime(2024, 1, 2, 3, 4, 5, tzinfo=dt_timezone.utc)
        model = SimpleNamespace(
            task_id="tid",
            task_name="T",
            description="d",
            status="open",
            priority=2,
            deadline=dt,
            created_at=dt,
            completed_at=None,
        )
        snap = task_snapshot(model)
        self.assertEqual(snap["task_id"], "tid")
        self.assertEqual(snap["priority"], 2)
        self.assertIn("deadline", snap)

    def test_task_snapshot_wraps_domain(self):
        inner = SimpleNamespace(task_id="x", task_name="n", description=None, status="s", priority=0)
        wrapped = SimpleNamespace(_task=inner)
        snap = task_snapshot(wrapped)
        self.assertEqual(snap["task_id"], "x")

    def test_project_member_snapshot_none(self):
        self.assertIsNone(project_member_snapshot(None))

    def test_project_member_snapshot_no_id(self):
        self.assertIsNone(project_member_snapshot(SimpleNamespace()))

    def test_project_member_snapshot_username_from_business_user(self):
        bu = SimpleNamespace(username="alice", user_id="u1")
        pm = SimpleNamespace(
            project_member_id="m1",
            user=bu,
            status="Alive",
            hp=10,
            max_hp=20,
            score=5,
        )
        snap = project_member_snapshot(pm)
        self.assertEqual(snap["username"], "alice")
        self.assertEqual(snap["project_member_id"], "m1")

    def test_project_member_username_via_auth_user(self):
        auth = SimpleNamespace(username="bob")
        bu = SimpleNamespace(username=None, auth_user=auth, user_id="u2")
        pm = SimpleNamespace(
            project_member_id="m2",
            user=bu,
            status="Alive",
            hp=None,
            max_hp=None,
            score=None,
        )
        snap = project_member_snapshot(pm)
        self.assertEqual(snap["username"], "bob")
