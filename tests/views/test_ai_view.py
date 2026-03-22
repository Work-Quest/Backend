from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from tests.drf_helpers import attach_authenticated_user

from api.views.ai_view import analyze_sentiment


class AiViewTest(SimpleTestCase):
    def test_analyze_sentiment_requires_text(self):
        factory = APIRequestFactory()
        request = factory.post("/ai/sentiment/", {}, format="json")
        attach_authenticated_user(request)

        response = analyze_sentiment(request)

        self.assertEqual(response.status_code, 400)
