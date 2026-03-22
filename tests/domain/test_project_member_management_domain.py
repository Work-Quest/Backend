from types import SimpleNamespace

from django.test import SimpleTestCase

from api.domains.project_member import ProjectMember as ProjectMemberDomain
from api.domains.project_member_management import ProjectMemberManagement


class ProjectMemberManagementDomainTest(SimpleTestCase):
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
