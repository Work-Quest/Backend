from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api.services.cache_service import CacheKeys, CacheService


class CacheServiceTest(SimpleTestCase):
    @patch("api.services.cache_service.cache")
    def test_delete_delegates_to_django_cache(self, mock_cache):
        CacheService().delete("some-key")
        mock_cache.delete.assert_called_once_with("some-key")

    @patch("api.services.cache_service.cache")
    def test_get_set_delete_many_read_write_through(self, mock_cache):
        svc = CacheService()
        mock_cache.get.return_value = None

        self.assertIsNone(svc.get("k"))
        mock_cache.get.assert_called_with("k")

        svc.set("k2", {"a": 1}, ttl_seconds=10)
        mock_cache.set.assert_called_with("k2", {"a": 1}, timeout=10)

        mock_cache.get.return_value = {"hit": True}
        self.assertEqual(svc.read_through(key="k3", ttl_seconds=5, loader=lambda: 123), {"hit": True})

        mock_cache.get.return_value = None
        self.assertEqual(svc.read_through(key="k4", ttl_seconds=2, loader=lambda: 99), 99)
        mock_cache.set.assert_called()

        svc.write_through(key="k5", value=7, ttl_seconds=1)
        mock_cache.set.assert_called()

        svc.delete_many(["a", "b"])
        mock_cache.delete_many.assert_called_once_with(["a", "b"])

    @patch("api.services.cache_service.cache")
    def test_delete_pattern_uses_backend_deleter(self, mock_cache):
        mock_cache.delete_pattern = MagicMock(return_value=3)
        n = CacheService().delete_pattern("p:*")
        self.assertEqual(n, 3)
        mock_cache.delete_pattern.assert_called_once_with("p:*")

    @patch("api.services.cache_service.cache")
    def test_delete_pattern_fallback_redis_scan(self, mock_cache):
        mock_cache.delete_pattern = None
        mock_cache.make_key = lambda p: f"px:{p}"
        fake_conn = MagicMock()
        fake_conn.scan_iter.return_value = ["k1", "k2"]
        with patch("django_redis.get_redis_connection", return_value=fake_conn):
            n = CacheService().delete_pattern("pat*")
        self.assertEqual(n, 2)

    @patch("api.services.cache_service.cache")
    def test_delete_pattern_deleter_exception_falls_back(self, mock_cache):
        mock_cache.delete_pattern = MagicMock(side_effect=RuntimeError("backend"))
        mock_cache.make_key = lambda p: f"px:{p}"
        fake_conn = MagicMock()
        fake_conn.scan_iter.return_value = []
        with patch("django_redis.get_redis_connection", return_value=fake_conn):
            n = CacheService().delete_pattern("z")
        self.assertEqual(n, 0)

    def test_cache_keys_factory(self):
        k = CacheKeys(namespace="ns")
        self.assertIn("ns", k.key("a", None, "b"))
        self.assertIn("game", k.project_boss("p"))

    @patch("api.services.cache_service.cache")
    def test_invalidate_helpers(self, mock_cache):
        mock_cache.delete_pattern = MagicMock(return_value=0)
        svc = CacheService()
        svc.invalidate_project_game("pid")
        svc.invalidate_project_member_items("pid", "mid")
        svc.invalidate_project_member_items("pid")
        svc.invalidate_project_member_status_effects("pid", "mid")
        svc.invalidate_project_member_status_effects("pid")
        svc.invalidate_project_members("pid")
        svc.invalidate_user_projects("uid")
        svc.invalidate_project_logs("pid")
        svc.invalidate_project_tasks("pid")
        svc.invalidate_all_business_users()
        self.assertTrue(mock_cache.delete.called or mock_cache.delete_many.called)
