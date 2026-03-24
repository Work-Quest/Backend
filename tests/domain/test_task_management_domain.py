from types import SimpleNamespace

from django.test import SimpleTestCase

from api.domains.task import Task as TaskDomain
from api.domains.task_management import TaskManagement


class TaskManagementDomainTest(SimpleTestCase):
    def test_get_task_from_cached_task_list(self):
        tm = TaskManagement.__new__(TaskManagement)
        tm.project = SimpleNamespace()
        tmodel = SimpleNamespace(
            task_id="tid-1",
            project=tm.project,
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
        td = TaskDomain(tmodel)
        tm._tasks = [td]

        found = tm.get_task("tid-1")
        self.assertIsNotNone(found)
        self.assertEqual(str(found.task_id), "tid-1")

    def test_get_task_returns_none_when_missing_from_cache(self):
        tm = TaskManagement.__new__(TaskManagement)
        tm.project = SimpleNamespace()
        tm._tasks = []

        self.assertIsNone(tm.get_task("missing"))
