from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from api.domains.boss import Boss
from api.domains.project import Project
from api.domains.project_member import ProjectMember
from api.domains.trust_score_policy import AlignmentTrustScorePolicy
from api.dtos.review_dto import TaskFacts
from api.services.auth_service import login_user
from api.services.cache_service import CacheKeys
from api.services.join_service import JoinService
from api.services.log_service import TaskLogQueryService
from api.views.auth_view import _cookie_kwargs
from api.views.log_view import _parse_time_begin


class DomainRepresentativeTests(SimpleTestCase):
    def test_project_member_attacked_clamps_hp_to_zero(self):
        member_model = SimpleNamespace(hp=10, max_hp=100, save=lambda **_: None)
        member = ProjectMember(member_model)

        member.attacked(999)

        self.assertEqual(member.hp, 0)

    def test_boss_max_hp_validation(self):
        boss_model = SimpleNamespace(hp=10, max_hp=100, save=lambda **_: None)
        boss = Boss(boss_model)

        with self.assertRaises(ValueError):
            boss.max_hp = 0

    def test_project_check_access_requires_member_and_working_status(self):
        project_model = SimpleNamespace(status="Working")
        domain = Project.__new__(Project)
        domain._project = project_model
        domain._project_member_management = SimpleNamespace(is_member=lambda _: True)

        self.assertTrue(domain.check_access(user=object()))

    def test_alignment_policy_returns_expected_structure(self):
        facts = TaskFacts(
            priority=3,
            created_at_ts=1.0,
            completed_at_ts=2.0,
            deadline_ts=3.0,
        )
        result = AlignmentTrustScorePolicy().compute(facts, sentiment_score=4)
        self.assertIn("weight_sentiment_score", result)
        self.assertIn("alignment_score", result)


class ServiceRepresentativeTests(SimpleTestCase):
    def test_cache_keys_builds_namespaced_key(self):
        keys = CacheKeys(namespace="ns")
        self.assertEqual(keys.project_boss("p1"), "ns:game:project_boss:p1")

    def test_join_service_normalize_emails(self):
        out = JoinService._normalize_emails(["A@X.com", " a@x.com ", "", None, "b@x.com"])
        self.assertEqual(out, ["a@x.com", "b@x.com"])

    @patch("api.services.auth_service.authenticate", return_value=None)
    def test_login_user_returns_none_tokens_for_invalid_credentials(self, _mock_auth):
        user, tokens = login_user("unknown", password="bad")
        self.assertIsNone(user)
        self.assertIsNone(tokens)

    def test_log_service_groups_unknown_event_type(self):
        grouped = TaskLogQueryService.group_logs_by_event_type(
            [SimpleNamespace(event_type=None), SimpleNamespace(event_type="X")]
        )
        self.assertIn("UNKNOWN", grouped)
        self.assertIn("X", grouped)


class ViewRepresentativeTests(SimpleTestCase):
    def test_cookie_kwargs_defaults(self):
        kwargs = _cookie_kwargs()
        self.assertTrue(kwargs["httponly"])
        self.assertEqual(kwargs["path"], "/")

    def test_parse_time_begin_accepts_date_string(self):
        dt = _parse_time_begin("2026-03-01")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)

    def test_parse_time_begin_rejects_invalid_value(self):
        with self.assertRaises(ValueError):
            _parse_time_begin("not-a-date")
