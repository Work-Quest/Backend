from unittest.mock import patch

from django.test import SimpleTestCase

from api.services.auth_service import login_user


class AuthServiceTest(SimpleTestCase):
    @patch("api.services.auth_service.authenticate", return_value=None)
    def test_login_user_returns_none_when_authenticate_fails(self, _mock_auth):
        user, tokens = login_user("unknown", password="bad")
        self.assertIsNone(user)
        self.assertIsNone(tokens)
