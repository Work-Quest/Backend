from django.test import SimpleTestCase

from api.services.cache_service import CacheKeys


class CacheKeysTest(SimpleTestCase):
    def test_project_boss_key_is_namespaced(self):
        keys = CacheKeys(namespace="ns")
        self.assertEqual(keys.project_boss("p1"), "ns:game:project_boss:p1")
