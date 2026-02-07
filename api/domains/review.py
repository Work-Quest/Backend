from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Optional, Literal, Protocol

from api.models import Item
from api.models import Effect
from api.dtos.review_dto import TaskFacts
from api.domains.trust_score_policy import TrustScorePolicy, AlignmentTrustScorePolicy



class Review:
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
        if self._effects_loaded == False:
            for e in Effect.objects.all():
                if e.effect_porality == "GOOD":
                    if e.rare_level == 1:
                        self.good_common_effects(e)
                    elif e.rare_level == 2:
                        self.good_rare_effects.append(e)
                    elif e.rare_level == 3:
                        self.good_epic_effects.append(e)
                else:
                    if e.rare_level == 1:
                        self.bad_common_effects(e)
                    elif e.rare_level == 2:
                        self.bad_rare_effects.append(e)

        self._effects_loaded == True
        

    def calculate_player_score(self, facts: TaskFacts, sentiment_score:int ):
        """
        Calculate player recieved score from review other player by weight from alignment score
        """
        scores = self.trust_policy.compute(facts, sentiment_score)
        # normalize alignment_scote [-2,2] to [1,100]
        normalized_score = 1 + (scores["alignment_score"]) * 99 / 4
        return normalized_score + self.BASE_SCORE

    def decide_effect(self, facts: TaskFacts, sentiment_score:int):
        self._load_effects()
        scores = self.trust_policy.compute(facts, sentiment_score)
        score = scores["weight_sentiment_score"]

        
        if 2 > score > 1:
            effect = random.choice(self.bad_rare_effects)
        elif 3 > score >= 2:
            effect = random.choice(self.bad_common_effects)
        elif 4 > score >= 3:
            effect = random.choice(self.good_common_effects)
        elif 5 > score >= 4:
            effect = random.choice(self.good_rare_effects)
        elif score == 5:
            effect = random.choice(self.good_epic_effects)

        # random if user will recieve Item of effect imeadiately
        choice = ["effect", "item"]
        rand_choice = random.choice(choice)
        if rand_choice == "item":
            item = Item.object.get(effect=effect)
            return item
        return effect
           
    # name = models.CharField(max_length=100)
    # description = models.TextField(blank=True)
    # status_effects = models.ManyToManyField(
    #     StatusEffect,
    #     blank=True,
    #     related_name="items"
    # )
    # created_at = models.DateTimeField(auto_now_add=True)

        