from django.test import SimpleTestCase

from api.domains.review import Review
from api.dtos.review_dto import TaskFacts


class ReviewDomainTest(SimpleTestCase):
    def test_calculate_player_score_returns_int(self):
        review = Review()
        facts = TaskFacts(
            priority=3,
            created_at_ts=1.0,
            completed_at_ts=2.0,
            deadline_ts=3.0,
        )
        score = review.calculate_player_score(facts, sentiment_score=4)
        self.assertIsInstance(score, int)
        self.assertGreaterEqual(score, 1)
