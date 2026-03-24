from types import SimpleNamespace

from django.test import SimpleTestCase

from api.domains.project_member import ProjectMember


class ProjectMemberDomainTest(SimpleTestCase):
    def test_attacked_clamps_hp_to_zero(self):
        member_model = SimpleNamespace(hp=10, max_hp=100, save=lambda **_: None)
        member = ProjectMember(member_model)

        member.attacked(999)

        self.assertEqual(member.hp, 0)
