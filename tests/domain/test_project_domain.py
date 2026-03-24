from types import SimpleNamespace

from django.test import SimpleTestCase

from api.domains.project import Project


class ProjectDomainTest(SimpleTestCase):
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
