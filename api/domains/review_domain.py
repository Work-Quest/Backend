from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal, Protocol

from api.domains.review_types import QualityLabel, TaskFacts
from api.domains.trust_score_policy import TrustScorePolicy, AlignmentTrustScorePolicy
from api.domains.sentiment_quality_policy import LexiconSentimentQualityPolicy


class QualityPolicy(Protocol):
    """
    Domain concept: map review text -> quality label (-1/0/1).
    Implementation can be simple rules or call an external AI model.
    """

    def score(self, *, text: str, facts: TaskFacts) -> QualityLabel: ...


class NeutralQualityPolicy:
    """Skeleton AI policy: always returns neutral (0). Replace with real sentiment/quality AI."""

    def score(self, *, text: str, facts: TaskFacts) -> QualityLabel:
        return 0


@dataclass(frozen=True)
class ReviewSignals:
    """
    Signals used by the scoring formulas.
    - quality: -1, 0, 1
    - trust_score: [0, 1]
    """

    quality: QualityLabel
    trust_score: float


@dataclass(frozen=True)
class ReviewScores:
    """
    Calculated scores:
    - score_receive: reward to reviewer for supporting others
    - review_score: score that determines effect applied to receiver
    """

    score_receive: float
    review_score: float


@dataclass(frozen=True)
class GameEffectDecision:
    """
    High-level effect decision (skeleton).
    You can later expand this to a richer schema (multiple effects, items, durations, etc.)
    """

    kind: Literal["BUFF", "DEBUFF", "NONE"]
    damage_modifier_pct: Optional[float] = None  # e.g. +0.10 means +10% next attack
    heal_pct: Optional[float] = None  # immediate heal as % of max_hp
    hp_delta_pct: Optional[float] = None  # immediate hp decrease as % of max_hp


class ReviewDomain:
    """
    Review business logic (game-related).

    Domain responsibilities:
    - Define AI/trust as domain concepts (policies)
    - Convert (task facts + review text) => signals
    - Apply formulas:
        score_receive = trust_score * base_score
        review_score  = trust_score * (base_score * quality)
    - Map review_score to buff/debuff decision
    """

    def __init__(
        self,
        base_score: float = 0.1,
        quality_policy: QualityPolicy | None = None,
        trust_policy: TrustScorePolicy | None = None,
    ):
        self.base_score = base_score
        # default to in-repo lexicon sentiment so the system is functional out of the box
        self.quality_policy = quality_policy or LexiconSentimentQualityPolicy()
        self.trust_policy = trust_policy or AlignmentTrustScorePolicy()

    def build_signals(self, *, facts: TaskFacts, review_text: str) -> ReviewSignals:
        quality = self.quality_policy.score(text=review_text, facts=facts)
        trust_score = self.trust_policy.compute(facts=facts, ai_quality=quality)
        return ReviewSignals(quality=quality, trust_score=trust_score)

    def calculate_scores(self, signals: ReviewSignals) -> ReviewScores:
        trust = max(0.0, min(1.0, float(signals.trust_score)))
        quality = int(signals.quality)

        score_receive = trust * self.base_score
        review_score = trust * (self.base_score * quality)
        return ReviewScores(score_receive=score_receive, review_score=review_score)

    def decide_effect(self, scores: ReviewScores) -> GameEffectDecision:
        if scores.review_score > 0:
            tier = self._tier(scores.review_score)
            pct = {1: 0.05, 2: 0.10, 3: 0.15}[tier]
            return GameEffectDecision(kind="BUFF", damage_modifier_pct=pct, heal_pct=pct)

        if scores.review_score < 0:
            tier = self._tier(abs(scores.review_score))
            pct = {1: 0.05, 2: 0.10, 3: 0.15}[tier]
            return GameEffectDecision(kind="DEBUFF", damage_modifier_pct=pct, hp_delta_pct=pct)

        return GameEffectDecision(kind="NONE")

    def _tier(self, magnitude: float) -> int:
        if magnitude >= (self.base_score * 1.0):
            return 3
        if magnitude >= (self.base_score * 0.66):
            return 2
        return 1


