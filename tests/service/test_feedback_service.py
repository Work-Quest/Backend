from django.test import SimpleTestCase, override_settings

from api.services.feedback_service import feedbackService


class FeedbackServiceTest(SimpleTestCase):
    @override_settings(AI_SERVICE_URL="http://ai.local", ETL_SERVICE_URL="http://etl.local")
    def test_init_reads_urls_from_settings(self):
        svc = feedbackService()
        self.assertEqual(svc.AI_SERVICE_URL, "http://ai.local")
        self.assertEqual(svc.ETL_SERVICE_URL, "http://etl.local")
