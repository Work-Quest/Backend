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

    @patch("api.services.task_service.Project")
    @patch("api.services.task_service.ProjectModel.objects.get")
    def test_get_all_tasks_returns_prefetched_queryset_when_access_granted(
        self, mock_get, mock_project_cls
    ):
        mock_get.return_value = MagicMock()
        mock_final_qs = MagicMock()
        mock_chain = MagicMock()
        mock_chain.prefetch_related.return_value = mock_final_qs
        tm = MagicMock()
        tm.get_all_tasks.return_value = mock_chain
        domain = MagicMock()
        domain.check_access.return_value = True
        domain._task_management = tm
        mock_project_cls.return_value = domain

        svc = TaskService("00000000-0000-0000-0000-000000000000", user=MagicMock())
        out = svc.get_all_tasks()

        self.assertIs(out, mock_final_qs)
        mock_chain.prefetch_related.assert_called_once_with(
            "assigned_members__project_member__user"
        )
