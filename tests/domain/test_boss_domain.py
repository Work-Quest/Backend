from types import SimpleNamespace

from django.test import SimpleTestCase

from api.domains.boss import Boss


class BossDomainTest(SimpleTestCase):
    def test_max_hp_must_be_positive(self):
        boss_model = SimpleNamespace(hp=10, max_hp=100, save=lambda **_: None)
        boss = Boss(boss_model)

        with self.assertRaises(ValueError):
            boss.max_hp = 0

    def test_attacked_clamps_at_zero_hp(self):
        boss_model = SimpleNamespace(hp=50, max_hp=100, save=lambda **_: None)
        boss = Boss(boss_model)

        boss.attacked(999)

        self.assertEqual(boss.hp, 0)
