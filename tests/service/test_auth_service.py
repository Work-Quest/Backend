from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api.services.auth_service import login_user


class AuthServiceTest(SimpleTestCase):
    @patch("api.services.auth_service.authenticate", return_value=None)
    def test_login_user_returns_none_when_authenticate_fails(self, _mock_auth):
        user, tokens = login_user("unknown", password="bad")
        self.assertIsNone(user)
        self.assertIsNone(tokens)

    @patch("api.services.auth_service.RefreshToken")
    @patch("api.services.auth_service.authenticate")
    def test_login_user_returns_user_and_tokens_when_authenticate_succeeds(
        self, mock_auth, mock_refresh_cls
    ):
        mock_user = MagicMock()
        mock_auth.return_value = mock_user
        mock_access = MagicMock()
        mock_access.__str__ = lambda self=None: "access-jwt"
        mock_refresh = MagicMock()
        mock_refresh.access_token = mock_access
        mock_refresh.__str__ = lambda self=None: "refresh-jwt"
        mock_refresh_cls.for_user.return_value = mock_refresh

        user, tokens = login_user("alice", password="secret")

        self.assertIs(user, mock_user)
        self.assertEqual(
            tokens,
            {"access": "access-jwt", "refresh": "refresh-jwt"},
        )
