from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api.domains.project_member import ProjectMember as ProjectMemberDomain
from api.domains.project_member_management import ProjectMemberManagement


class ProjectMemberManagementDomainTest(SimpleTestCase):
    @patch("api.domains.project_member_management.ProjectMemberModel.objects.filter")
    def test_members_loads_and_caches_domain_members(self, mock_filter):
        member_model = SimpleNamespace(
            project_member_id="abc-123",
            hp=100,
            max_hp=100,
            score=0,
            status="Alive",
            user=object(),
            project=object(),
            save=lambda **_: None,
        )
        mock_filter.return_value.select_related.return_value = [member_model]

        project = object()
        pmm = ProjectMemberManagement(project)

        first = pmm.members
        second = pmm.members

        mock_filter.assert_called_once_with(project=project)
        self.assertIs(first, second)
        self.assertEqual(len(first), 1)
        self.assertEqual(str(first[0].project_member_id), "abc-123")

    @patch("api.domains.project_member_management.ProjectMemberModel.objects.create")
    def test_add_member_creates_alive_member_and_clears_cache(self, mock_create):
        member_model = SimpleNamespace(
            project_member_id="new-id",
            hp=100,
            max_hp=100,
            score=0,
            status="Alive",
            user=object(),
            project=object(),
            save=lambda **_: None,
        )
        mock_create.return_value = member_model

        project = object()
        user = object()
        pmm = ProjectMemberManagement(project)
        pmm._members = ["stale"]

        created = pmm.add_member(user)

        mock_create.assert_called_once_with(
            project=project,
            user=user,
            hp=100,
            status="Alive",
        )
        self.assertIsInstance(created, ProjectMemberDomain)
        self.assertIsNone(pmm._members)

    def test_get_member_returns_matching_domain(self):
        inner = SimpleNamespace(
            project_member_id="abc-123",
            hp=100,
            max_hp=100,
            score=0,
            status="Alive",
            user=None,
            project=None,
            save=lambda **_: None,
        )
        pmm = ProjectMemberManagement.__new__(ProjectMemberManagement)
        pmm.project = object()
        pmm._members = [ProjectMemberDomain(inner)]

        found = pmm.get_member("abc-123")
        self.assertIsNotNone(found)
        self.assertEqual(str(found.project_member_id), "abc-123")

    def test_get_member_returns_none_when_missing(self):
        inner = SimpleNamespace(
            project_member_id="abc-123",
            hp=100,
            max_hp=100,
            score=0,
            status="Alive",
            user=None,
            project=None,
            save=lambda **_: None,
        )
        pmm = ProjectMemberManagement.__new__(ProjectMemberManagement)
        pmm.project = object()
        pmm._members = [ProjectMemberDomain(inner)]

        self.assertIsNone(pmm.get_member("missing-id"))

    def test_edit_member_updates_hp_and_status(self):
        save = MagicMock()
        inner = SimpleNamespace(
            project_member_id="abc-123",
            hp=100,
            max_hp=100,
            score=0,
            status="Alive",
            user=None,
            project=None,
            save=save,
        )
        pmm = ProjectMemberManagement.__new__(ProjectMemberManagement)
        pmm.project = object()
        pmm._members = [ProjectMemberDomain(inner)]

        updated = pmm.edit_member("abc-123", {"hp": 80, "status": "Dead"})

        self.assertIsNotNone(updated)
        self.assertEqual(updated.hp, 80)
        self.assertEqual(updated.status, "Dead")
        self.assertIsNone(pmm._members)
        self.assertEqual(save.call_count, 2)

    def test_edit_member_returns_none_for_unknown_member(self):
        pmm = ProjectMemberManagement.__new__(ProjectMemberManagement)
        pmm.project = object()
        pmm._members = []

        self.assertIsNone(pmm.edit_member("missing-id", {"hp": 80}))

    def test_remove_member_deletes_matching_member(self):
        deleted = []
        member = SimpleNamespace(id="member-1", delete=lambda: deleted.append(True))
        pmm = ProjectMemberManagement.__new__(ProjectMemberManagement)
        pmm.project = object()
        pmm._members = [member]

        removed = pmm.remove_member("member-1")

        self.assertTrue(removed)
        self.assertEqual(deleted, [True])
        self.assertEqual(pmm._members, [])

    def test_is_member_checks_existing_users(self):
        user = object()
        pmm = ProjectMemberManagement.__new__(ProjectMemberManagement)
        pmm.project = object()
        pmm._members = [SimpleNamespace(user=user), SimpleNamespace(user=object())]

        self.assertTrue(pmm.is_member(user))
        self.assertFalse(pmm.is_member(object()))
