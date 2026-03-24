from types import SimpleNamespace

from django.test import SimpleTestCase

from api.domains.task import Task


class TaskDomainTest(SimpleTestCase):
    def test_is_completed_when_status_done(self):
        model = SimpleNamespace(
            task_id="t1",
            project=None,
            priority=1,
            task_name="n",
            description="",
            status="done",
            deadline=None,
            created_at=None,
            completed_at=None,
            save=lambda **_: None,
            delete=lambda: None,
        )
        task = Task(model)
        self.assertTrue(task.is_completed())

    def test_is_completed_false_for_backlog(self):
        model = SimpleNamespace(
            task_id="t1",
            project=None,
            priority=1,
            task_name="n",
            description="",
            status="backlog",
            deadline=None,
            created_at=None,
            completed_at=None,
            save=lambda **_: None,
            delete=lambda: None,
        )
        task = Task(model)
        self.assertFalse(task.is_completed())
