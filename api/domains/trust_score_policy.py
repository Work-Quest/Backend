from __future__ import annotations

from typing import Protocol

from api.dtos.review_dto import TaskFacts


class TrustScorePolicy(Protocol):
    """
    Comput weight score by alignment between objective task facts (done date/priority) and user's sentiment analysis score.
    """

    def compute(self, *, facts: TaskFacts) -> float: ...


class AlignmentTrustScorePolicy:
    """
    Tust score policy for weight sentiment analysis with actual outcome
    AI sentiment score = [1,2,3,4,5]
    """

    def __init__(self, *, on_time_grace_ratio: float = 0.10):
        self.on_time_grace_ratio = on_time_grace_ratio

    def compute(self, facts: TaskFacts, sentiment_score: int):
        """
        return weighted score and 
        """
        evidence = self._objective_quality_label(facts)
        k = self._evidence_weight(facts)
        normalized = (sentiment_score - 3.0) / 2.0
        alignment_score = evidence - normalized
        weight = alignment_score * k
        weighted_score = sentiment_score + weight
        return {
            "weight_sentiment_score" : self._clamp01(weighted_score),
            "alignment_score": alignment_score,
        }

    def _objective_quality_label(self, facts: TaskFacts) :
        """
        Convert task completion timing + priority into an expected quality label.
        negative = -1
        netural = 0
        positive = 1
        """
        if facts.completed_at_ts is None:
            return 0

        if facts.deadline_ts is None:
            duration = max(1.0, facts.completed_at_ts - facts.created_at_ts)
            p = max(1, int(facts.priority))
            if p >= 3 and duration < 2 * 24 * 3600:
                return 1
            if p >= 3 and duration > 7 * 24 * 3600:
                return -1
            return 0

        total_window = max(1.0, facts.deadline_ts - facts.created_at_ts)
        slack = facts.deadline_ts - facts.completed_at_ts  # + early / - late
        slack_ratio = slack / total_window

        p = max(1, int(facts.priority))
        adjusted = slack_ratio * (1.0 + 0.25 * (p - 1))

        if adjusted >= self.on_time_grace_ratio:
            return 1
        if adjusted <= -self.on_time_grace_ratio:
            return -1
        return 0

    def _evidence_weight(self, facts: TaskFacts) -> float:
        if facts.completed_at_ts is None:
            return 1.0
        return 1.5

    def _clamp01(self, x: float) -> float:
        return max(1.0, min(5.0, x))





