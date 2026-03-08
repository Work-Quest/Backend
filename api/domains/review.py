from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Optional, Literal, Protocol

from api.models.Effect import Effect
from api.dtos.review_dto import TaskFacts
from api.domains.trust_score_policy import TrustScorePolicy, AlignmentTrustScorePolicy



class Review:
    """
    Review business logic (game-related)
    """

    def __init__(self):
        self.BASE_SCORE = 100
        self.trust_policy = AlignmentTrustScorePolicy()

        self._effects_loaded = False
        
        self.good_common_effects = []
        self.good_rare_effects = []
        self.good_epic_effects = []
        self.bad_common_effects = []
        self.bad_rare_effects = []


    def _load_effects(self):
        if self._effects_loaded:
            return

        # reset buckets (avoid duplicates if called multiple times)
        self.good_common_effects = []
        self.good_rare_effects = []
        self.good_epic_effects = []
        self.bad_common_effects = []
        self.bad_rare_effects = []

        for e in Effect.objects.all():
            rare = int(e.rare_level or 1)
            is_good = (e.effect_polarity == "GOOD")

            if is_good:
                if rare == 1:
                    self.good_common_effects.append(e)
                elif rare == 2:
                    self.good_rare_effects.append(e)
                else:
                    self.good_epic_effects.append(e)
            else:
                if rare == 1:
                    self.bad_common_effects.append(e)
                else:
                    self.bad_rare_effects.append(e)

        self._effects_loaded = True
        

    def calculate_player_score(self, facts: TaskFacts, sentiment_score:int ):
        """
        Calculate player received score from review other player by weight from alignment score
        """
        scores = self.trust_policy.compute(facts, sentiment_score)
        # normalize alignment_scote [-2,2] to [1,100]
        normalized_score = 1 + (scores["alignment_score"]) * 99 / 4
        # keep score integral (ProjectMember.score is an IntegerField)
        return int(round(normalized_score + self.BASE_SCORE))

    def decide_effect(self, facts: TaskFacts, sentiment_score:int):
        self._load_effects()
        scores = self.trust_policy.compute(facts, sentiment_score)
        score = float(scores["weight_sentiment_score"])

        def _pick(pool):
            return random.choice(pool) if pool else None

        effect = None
        # include score == 1 case (possible due to clamp) as "worst" bucket
        if score <= 1:
            effect = _pick(self.bad_rare_effects) or _pick(self.bad_common_effects)
        
        if 2 > score > 1:
            effect = _pick(self.bad_rare_effects)
        elif 3 > score >= 2:
            effect = _pick(self.bad_common_effects)
        elif 4 > score >= 3:
            effect = _pick(self.good_common_effects)
        elif 5 > score >= 4:
            effect = _pick(self.good_rare_effects)
        elif score == 5:
            effect = _pick(self.good_epic_effects) or _pick(self.good_rare_effects) or _pick(self.good_common_effects)
                    
        return effect
           
    # name = models.CharField(max_length=100)
    # description = models.TextField(blank=True)
    # status_effects = models.ManyToManyField(
    #     StatusEffect,
    #     blank=True,
    #     related_name="items"
    # )
    # created_at = models.DateTimeField(auto_now_add=True)

        