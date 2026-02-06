from __future__ import annotations

import re
from typing import Iterable

from api.domains.review_types import QualityLabel, TaskFacts
from api.services.ai_service import AIService


class LexiconSentimentQualityPolicy:
    """
    Lightweight, dependency-free sentiment/quality policy.
    Maps review text -> QualityLabel (-1/0/1) using simple lexicon scoring.
    """

    POSITIVE: set[str] = {
        "great",
        "good",
        "excellent",
        "awesome",
        "amazing",
        "nice",
        "perfect",
        "helpful",
        "thanks",
        "thank you",
        "well done",
        "fast",
        "on time",
        "quick",
        "love",
    }
    NEGATIVE: set[str] = {
        "bad",
        "terrible",
        "awful",
        "slow",
        "late",
        "rude",
        "unhelpful",
        "poor",
        "worse",
        "worst",
        "hate",
        "scam",
        "never",
        "disappointed",
    }

    def score(self, *, text: str, facts: TaskFacts) -> QualityLabel:
        _ = facts  # domain signature includes task facts, but lexicon ignores them for now.

        if not text or not text.strip():
            return 0

        tokens = self._tokens(text)
        pos = sum(1 for t in tokens if t in self.POSITIVE)
        neg = sum(1 for t in tokens if t in self.NEGATIVE)

        if pos > neg:
            return 1
        if neg > pos:
            return -1
        return 0

    def _tokens(self, text: str) -> Iterable[str]:
        # keep basic word chars; also keep some multi-word lexicon items by checking raw text
        lowered = text.lower()
        words = re.findall(r"[a-zA-Z']+", lowered)

        # include original lowered string for phrase matching
        for w in words:
            yield w
        for phrase in ("thank you", "well done", "on time"):
            if phrase in lowered:
                yield phrase


class HuggingFaceSentimentQualityPolicy:
    """
    AI-backed policy that uses `AIService` which, by default, uses the
    `HuggingFaceSentimentAnalyzer` adapter.
    """

    def __init__(self, *, ai_service: AIService | None = None):
        self.ai_service = ai_service or AIService()
        self._fallback = LexiconSentimentQualityPolicy()

    def score(self, *, text: str, facts: TaskFacts) -> QualityLabel:
        if not text or not text.strip():
            return 0

        try:
            result = self.ai_service.analyze_sentiment(text)
            quality = self._map_result_to_quality(result)
            return quality if quality in (-1, 0, 1) else 0
        except Exception:
            # Keep reviews functional even if HF is misconfigured/unavailable.
            return self._fallback.score(text=text, facts=facts)

    def _map_result_to_quality(self, result: dict) -> QualityLabel:
        """
        Adapter currently returns:
          {"label": <input text>, "score": <hf_result>}

        Where hf_result is typically a list of items containing label/score
        (e.g. "1 star".."5 stars") for `nlptown/bert-base-multilingual-uncased-sentiment`.
        """

        raw = result.get("score")

        # Handle list of classification outputs.
        if isinstance(raw, (list, tuple)) and raw:
            best = self._best_item(raw)
            label = self._get_label(best)
            return self._label_to_quality(label)

        # Handle common alternative outputs (dict with label).
        label = result.get("label")
        if isinstance(label, str):
            return self._label_to_quality(label)

        return 0

    def _best_item(self, items):
        def _score(x):
            if hasattr(x, "score"):
                return float(getattr(x, "score"))
            if isinstance(x, dict) and "score" in x:
                return float(x["score"])
            return 0.0

        return max(items, key=_score)

    def _get_label(self, item) -> str:
        if hasattr(item, "label"):
            return str(getattr(item, "label"))
        if isinstance(item, dict) and "label" in item:
            return str(item["label"])
        return ""

    def _label_to_quality(self, label: str) -> QualityLabel:
        if not label:
            return 0

        l = label.strip().lower()

        # "1 star", "2 stars", ... (nlptown model)
        m = re.match(r"^([1-5])\s*star", l)
        if m:
            stars = int(m.group(1))
            if stars <= 2:
                return -1
            if stars == 3:
                return 0
            return 1

        if "positive" in l:
            return 1
        if "negative" in l:
            return -1
        return 0


