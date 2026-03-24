from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from tests.drf_helpers import attach_authenticated_user

from api.views.log_view import (
    _parse_time_begin,
    get_all_task_logs,
    get_project_logs,
    get_project_logs_grouped,
)


class LogViewTest(SimpleTestCase):
    def test_parse_time_begin_accepts_date_only(self):
        dt = _parse_time_begin("2026-03-01")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)

    def test_parse_time_begin_none_and_empty(self):
        self.assertIsNone(_parse_time_begin(None))
        self.assertIsNone(_parse_time_begin("  "))

    def test_parse_time_begin_iso(self):
        dt = _parse_time_begin("2026-03-01T12:00:00Z")
        self.assertIsNotNone(dt)

    def test_parse_time_begin_rejects_garbage(self):
        with self.assertRaises(ValueError):
            _parse_time_begin("not-a-date")

    @patch("api.views.log_view.TaskLogQueryService")
    @patch("api.views.log_view.CacheService")
    @patch("api.views.log_view.ProjectDomain")
    @patch("api.views.log_view.Project.objects.get")
    @patch("api.views.log_view.BusinessUser.objects.get")
    def test_get_project_logs_success(self, mock_bu, mock_proj, mock_dom, mock_cache_cls, mock_log_svc):
        mock_bu.return_value = MagicMock()
        proj = MagicMock()
        mock_proj.return_value = proj
        mock_dom.return_value.check_access.return_value = True
        mock_log_svc.return_value.get_game_logs.return_value = []
        cache = MagicMock()
        cache.keys.project_game_logs.return_value = "lg"
        cache.read_through.side_effect = lambda **kw: kw["loader"]()
        mock_cache_cls.return_value = cache
        factory = APIRequestFactory()
        request = factory.get("/logs/?time_begin=2026-01-01")
        attach_authenticated_user(request)
        r = get_project_logs(request, "00000000-0000-0000-0000-000000000001")
        self.assertEqual(r.status_code, 200)

    @patch("api.views.log_view.Project.objects.get", side_effect=Exception("missing"))
    @patch("api.views.log_view.BusinessUser.objects.get")
    def test_get_project_logs_project_missing(self, mock_bu, _mock_proj):
        mock_bu.return_value = MagicMock()
        factory = APIRequestFactory()
        request = factory.get("/logs/")
        attach_authenticated_user(request)
        r = get_project_logs(request, "00000000-0000-0000-0000-000000000001")
        self.assertEqual(r.status_code, 400)

    @patch("api.views.log_view.TaskLogQueryService")
    @patch("api.views.log_view.CacheService")
    @patch("api.views.log_view.ProjectDomain")
    @patch("api.views.log_view.Project.objects.get")
    @patch("api.views.log_view.BusinessUser.objects.get")
    def test_get_project_logs_grouped(self, mock_bu, mock_proj, mock_dom, mock_cache_cls, mock_tls):
        mock_bu.return_value = MagicMock()
        mock_proj.return_value = MagicMock()
        mock_dom.return_value.check_access.return_value = True
        tls = MagicMock()
        tls.get_game_logs.return_value = []
        tls.group_logs_by_event_type.return_value = {}
        mock_tls.return_value = tls
        cache = MagicMock()
        cache.keys.project_game_logs_grouped.return_value = "kg"
        cache.read_through.side_effect = lambda **kw: kw["loader"]()
        mock_cache_cls.return_value = cache
        factory = APIRequestFactory()
        request = factory.get("/logs/g/?group_by=event_type")
        attach_authenticated_user(request)
        r = get_project_logs_grouped(request, "00000000-0000-0000-0000-000000000001")
        self.assertEqual(r.status_code, 200)

    @patch("api.views.log_view.TaskLogQueryService")
    def test_get_all_task_logs(self, mock_tls):
        mock_tls.return_value.get_all_logs.return_value = []
        factory = APIRequestFactory()
        request = factory.get("/all-logs/")
        r = get_all_task_logs(request)
        self.assertEqual(r.status_code, 200)
