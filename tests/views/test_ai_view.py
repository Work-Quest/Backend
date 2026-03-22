from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from tests.drf_helpers import attach_authenticated_user

from api.views.ai_view import analyze_sentiment


class AiViewTest(SimpleTestCase):
    @patch("api.views.ai_view.AIService")
    def test_analyze_sentiment_returns_service_result_when_text_present(self, mock_ai_cls):
        mock_ai_cls.return_value.analyze_sentiment.return_value = {
            "label": "POSITIVE",
            "score": 0.91,
        }
        factory = APIRequestFactory()
        request = factory.post(
            "/ai/sentiment/",
            {"text": "Shipped on time, great collaboration."},
            format="json",
        )
        attach_authenticated_user(request)

        response = analyze_sentiment(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["label"], "POSITIVE")
        mock_ai_cls.return_value.analyze_sentiment.assert_called_once()

    def test_analyze_sentiment_requires_text(self):
        factory = APIRequestFactory()
        request = factory.post("/ai/sentiment/", {}, format="json")
        attach_authenticated_user(request)

        response = analyze_sentiment(request)

        self.assertEqual(response.status_code, 400)
