from django.test import SimpleTestCase

from api.services.ai_service import AIService


class AIServiceTest(SimpleTestCase):
    def test_analyze_sentiment_uses_injected_analyzer(self):
        class FakeAnalyzer:
            def analyze(self, text: str):
                return {"label": "pos", "score": 0.9}

        svc = AIService(sentiment_analyzer=FakeAnalyzer())
        self.assertEqual(svc.analyze_sentiment("hello"), {"label": "pos", "score": 0.9})

    def test_analyze_sentiment_rejects_empty_text(self):
        svc = AIService(sentiment_analyzer=type("A", (), {"analyze": lambda self, t: {}})())
        with self.assertRaises(ValueError):
            svc.analyze_sentiment("   ")
