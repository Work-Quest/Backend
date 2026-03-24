from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api.models import TaskLog
from api.services.log_service import TaskLogQueryService


class LogServiceTest(SimpleTestCase):
    def test_group_logs_by_event_type_handles_unknown(self):
        grouped = TaskLogQueryService.group_logs_by_event_type(
            [SimpleNamespace(event_type=None), SimpleNamespace(event_type="X")]
        )
        self.assertIn("UNKNOWN", grouped)
        self.assertIn("X", grouped)

    def test_group_logs_by_category_combat_and_unknown(self):
        combat = SimpleNamespace(event_type=TaskLog.EventType.USER_ATTACK)
        unknown = SimpleNamespace(event_type=None)
        other = SimpleNamespace(event_type="CUSTOM_UNKNOWN")
        grouped = TaskLogQueryService.group_logs_by_category([combat, unknown, other])
        self.assertIn("COMBAT", grouped)
        self.assertIn("UNKNOWN", grouped)
        self.assertIn("OTHER", grouped)

    @patch.object(TaskLogQueryService, "_base_queryset")
    def test_get_game_logs_empty(self, mock_bq):
        qs = MagicMock()
        mock_bq.return_value = qs
        qs.filter.return_value = qs
        qs.order_by.return_value = []
        self.assertEqual(TaskLogQueryService().get_game_logs("00000000-0000-0000-0000-000000000001"), [])

    @patch.object(TaskLogQueryService, "_base_queryset")
    def test_get_all_logs_empty(self, mock_bq):
        qs = MagicMock()
        mock_bq.return_value = qs
        qs.filter.return_value = qs
        qs.order_by.return_value = []
        self.assertEqual(TaskLogQueryService().get_all_logs(time_begin=None), [])
