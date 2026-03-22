from django.test import SimpleTestCase

from api.services.join_service import JoinService


class JoinServiceTest(SimpleTestCase):
    def test_normalize_emails_dedupes_and_lowercases(self):
        out = JoinService._normalize_emails(["A@X.com", " a@x.com ", "", None, "b@x.com"])
        self.assertEqual(out, ["a@x.com", "b@x.com"])

    def test_build_invite_url_none_when_base_missing(self):
        self.assertIsNone(JoinService._build_invite_url("", "tok"))

    def test_build_invite_url_includes_token(self):
        url = JoinService._build_invite_url("https://app.example", "abc")
        self.assertIn("token=abc", url)
