from __future__ import annotations

from api.ai.adapters.huggingface_sentiment_analyzer import HuggingFaceSentimentAnalyzer
from api.ai.ports.sentiment_analyzer import SentimentAnalyzer

# try:
#     from api.ai.adapters.huggingface_sentiment_analyzer import HuggingFaceSentimentAnalyzer
# except Exception:  # pragma: no cover
#     HuggingFaceSentimentAnalyzer = None  # type: ignore[assignment]


class AIService:
    def __init__(self, *, sentiment_analyzer: SentimentAnalyzer | None = None):
        if sentiment_analyzer is not None:
            self.sentiment_analyzer = sentiment_analyzer
        elif HuggingFaceSentimentAnalyzer is not None:
            self.sentiment_analyzer = HuggingFaceSentimentAnalyzer()
        else:
            raise RuntimeError("No sentiment analyzer configured (HuggingFace adapter unavailable).")

    def analyze_sentiment(self, text: str) -> dict:
        if not text or not text.strip():
            raise ValueError("No sentiment text")

        return self.sentiment_analyzer.analyze(text)