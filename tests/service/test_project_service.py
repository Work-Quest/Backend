import uuid
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api.services.project_service import ProjectService


class ProjectServiceTest(SimpleTestCase):
    @patch("api.services.project_service.Project")
    def test_delete_project_returns_error_when_task_delete_fails(self, mock_project_cls):
        mock_project = MagicMock()
        task = MagicMock()
        task.delete.side_effect = RuntimeError("db error")
        mock_domain = MagicMock()
        mock_domain.TaskManagement.tasks = [task]
        mock_project_cls.return_value = mock_domain

        with patch(
            "api.services.project_service.ProjectModel.objects.get",
            return_value=mock_project,
        ):
            result = ProjectService().delete_project("pid")

        self.assertIn("error", result)

    @patch("api.services.project_service.timezone")
    @patch("api.services.project_service.Task.objects")
    @patch("api.services.project_service.ProjectModel.objects")
    def test_get_dashboard_data_shapes(self, mock_proj, mock_task, mock_tz):
        proj = MagicMock()
        proj.created_at.date.return_value = date(2025, 1, 1)
        proj.deadline = None
        mock_proj.get.return_value = proj
        qs = MagicMock()
        qs.filter.return_value = qs
        qs.count.return_value = 0
        qs.values.return_value = []
        qs.exists.return_value = False
        mock_task.filter.return_value = qs
        mock_tz.now.return_value.date.return_value = date(2025, 1, 5)
        out = ProjectService().get_dashboard_data(str(uuid.uuid4()))
        self.assertIn("taskStatusCounts", out)
        self.assertIn("burnDownData", out)

    @patch("api.services.project_service.ProjectDomain")
    @patch("api.services.project_service.ProjectMember.objects")
    def test_get_projects_maps_memberships(self, mock_pm, mock_dom):
        m = MagicMock()
        m.project = MagicMock()
        mock_pm.filter.return_value.select_related.return_value = [m]
        mock_dom.return_value = MagicMock(name="domain")
        out = ProjectService().get_projects("uid")
        self.assertEqual(len(out), 1)
