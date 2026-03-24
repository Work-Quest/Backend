from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api.domains.project import Project


class ProjectDomainTest(SimpleTestCase):
    @patch("api.domains.project.Game")
    @patch("api.domains.project.TaskManagement")
    @patch("api.domains.project.ProjectMemberManagement")
    def test_init_wires_management_and_game_dependencies(
        self, mock_member_mgmt, mock_task_mgmt, mock_game
    ):
        project_model = object()

        domain = Project(project_model)

        self.assertIs(domain.project, project_model)
        self.assertIs(domain.project_member_management, mock_member_mgmt.return_value)
        self.assertIs(domain.TaskManagement, mock_task_mgmt.return_value)
        self.assertIs(domain.game, mock_game.return_value)
        mock_member_mgmt.assert_called_once_with(project_model)
        mock_task_mgmt.assert_called_once_with(project_model)
        mock_game.assert_called_once_with(domain)

    def test_edit_project_metadata_updates_fields_and_saves(self):
        project_model = SimpleNamespace(
            project_name="Old",
            deadline="old-deadline",
            status="Working",
            total_tasks=1,
            completed_tasks=0,
            save=MagicMock(),
        )
        domain = Project.__new__(Project)
        domain._project = project_model

        updated = domain.edit_project_metadata(
            {
                "project_name": "New",
                "deadline": "new-deadline",
                "status": "Done",
                "total_tasks": 5,
                "completed_tasks": 3,
            }
        )

        self.assertIs(updated, project_model)
        self.assertEqual(project_model.project_name, "New")
        self.assertEqual(project_model.deadline, "new-deadline")
        self.assertEqual(project_model.status, "Done")
        self.assertEqual(project_model.total_tasks, 5)
        self.assertEqual(project_model.completed_tasks, 3)
        project_model.save.assert_called_once_with()

    def test_close_project_sets_closed_and_saves(self):
        project_model = SimpleNamespace(status="Working", save=MagicMock())
        domain = Project.__new__(Project)
        domain._project = project_model

        closed = domain.close_project()

        self.assertIs(closed, project_model)
        self.assertEqual(project_model.status, "closed")
        project_model.save.assert_called_once_with()

    def test_check_access_requires_member_and_working_status(self):
        project_model = SimpleNamespace(status="Working")
        domain = Project.__new__(Project)
        domain._project = project_model
        domain._project_member_management = SimpleNamespace(is_member=lambda _: True)

        self.assertTrue(domain.check_access(user=object()))

    def test_check_access_denied_when_not_working(self):
        project_model = SimpleNamespace(status="Done")
        domain = Project.__new__(Project)
        domain._project = project_model
        domain._project_member_management = SimpleNamespace(is_member=lambda _: True)

        self.assertFalse(domain.check_access(user=object()))

    def test_check_access_denied_when_user_is_not_member(self):
        project_model = SimpleNamespace(status="Working")
        domain = Project.__new__(Project)
        domain._project = project_model
        domain._project_member_management = SimpleNamespace(is_member=lambda _: False)

        self.assertFalse(domain.check_access(user=object()))

    def test_setup_boss_delegates_to_game(self):
        domain = Project.__new__(Project)
        domain._game = SimpleNamespace(initial_boss_setup=MagicMock(return_value="boss"))

        out = domain.setup_boss()

        self.assertEqual(out, "boss")
        domain._game.initial_boss_setup.assert_called_once_with()
