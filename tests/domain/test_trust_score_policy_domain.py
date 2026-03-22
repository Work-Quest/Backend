from django.test import SimpleTestCase

from api.domains.trust_score_policy import AlignmentTrustScorePolicy
from api.dtos.review_dto import TaskFacts


class TrustScorePolicyDomainTest(SimpleTestCase):
    def test_alignment_policy_returns_expected_keys(self):
        facts = TaskFacts(
            priority=3,
            created_at_ts=1.0,
            completed_at_ts=2.0,
            deadline_ts=3.0,
        )
        result = AlignmentTrustScorePolicy().compute(facts, sentiment_score=4)
        self.assertIn("weight_sentiment_score", result)
        self.assertIn("alignment_score", result)
