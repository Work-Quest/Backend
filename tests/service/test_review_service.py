from unittest.mock import MagicMock

from django.test import SimpleTestCase

from api.services.review_service import ReviewService


class ReviewServiceTest(SimpleTestCase):
    def test_create_review_report_requires_description(self):
        svc = ReviewService()
        with self.assertRaises(ValueError):
            svc.create_review_report({"task_id": "t", "description": "  "}, MagicMock(), "pid")

    def test_create_review_report_requires_ids(self):
        svc = ReviewService()
        with self.assertRaises(ValueError):
            svc.create_review_report({"description": "ok"}, MagicMock(), None)
