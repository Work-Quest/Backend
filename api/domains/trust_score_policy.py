from __future__ import annotations

from typing import Protocol

from api.domains.review_types import QualityLabel, TaskFacts


class TrustScorePolicy(Protocol):
    """
    Domain concept: compute trust score in [0,1].
    In your case: alignment between objective task facts (done date/priority) and AI quality.
    """

    def compute(self, *, facts: TaskFacts, ai_quality: QualityLabel) -> float: ...


class AlignmentTrustScorePolicy:
    """
    Trust score = alignment(objective_quality_from_task_facts, ai_quality).

    Skeleton rules:
    - derive objective label from (completed_at, deadline, priority)
    - compare objective label with AI quality (-1/0/1)
    - reduce trust if evidence is missing (e.g., no completed_at)
    """

    def __init__(self, *, on_time_grace_ratio: float = 0.10):
        self.on_time_grace_ratio = on_time_grace_ratio

    def compute(self, *, facts: TaskFacts, ai_quality: QualityLabel) -> float:
        objective = self._objective_quality_label(facts)

        if objective == ai_quality:
            base = 1.0
        elif objective == 0 or ai_quality == 0:
            base = 0.6
        else:
            base = 0.2

        evidence = self._evidence_weight(facts)
        return self._clamp01(base * evidence)

    def _objective_quality_label(self, facts: TaskFacts) -> QualityLabel:
        """
        Convert task completion timing + priority into an expected quality label.
        - completed_at missing => 0 (unknown/neutral)
        - deadline missing => rough duration heuristic (placeholder)
        - deadline present => compute slack vs available time window (priority-adjusted)
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
            return 0.4
        if facts.deadline_ts is None:
            return 0.7
        return 1.0

    def _clamp01(self, x: float) -> float:
        return max(0.0, min(1.0, float(x)))




