from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api.services.task_service import TaskService


class TaskServiceTest(SimpleTestCase):
    @patch("api.services.task_service.Project")
    @patch("api.services.task_service.ProjectModel.objects.get")
    def test_get_all_tasks_raises_when_access_denied(self, mock_get, mock_project_cls):
        mock_get.return_value = MagicMock()
        domain = MagicMock()
        domain.check_access.return_value = False
        mock_project_cls.return_value = domain

        svc = TaskService("00000000-0000-0000-0000-000000000000", user=MagicMock())

        with self.assertRaises(PermissionError):
            svc.get_all_tasks()
