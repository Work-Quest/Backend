from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from api.domains.report import Report


class ReportDomainTest(SimpleTestCase):
    def test_delete_delegates_to_model(self):
        deleted = []

        task = SimpleNamespace(task_id="t1")
        reporter_model = MagicMock()
        model = SimpleNamespace(
            report_id="r1",
            task=task,
            description="d",
            sentiment_score=3,
            created_at=None,
            reporter=reporter_model,
            save=lambda **_: None,
            delete=lambda: deleted.append(True),
        )
        domain = Report(model)

        domain.delete()

        self.assertEqual(deleted, [True])
