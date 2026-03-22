from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError

from api.cookie_authentication import CookieJWTAuthentication


class CookieJWTAuthenticationTest(SimpleTestCase):
    def test_authenticate_uses_valid_access_cookie(self):
        auth = CookieJWTAuthentication()
        request = MagicMock()
        request.COOKIES = {"access": "access-token"}
        user = MagicMock()
        validated = MagicMock()

        with patch.object(auth, "get_validated_token", return_value=validated) as gv, patch.object(
            auth, "get_user", return_value=user
        ) as gu:
            out = auth.authenticate(request)

        self.assertEqual(out, (user, validated))
        gv.assert_called_once_with("access-token")
        gu.assert_called_once_with(validated)

    def test_invalid_access_cookie_falls_back_to_header(self):
        auth = CookieJWTAuthentication()
        request = MagicMock()
        request.COOKIES = {"access": "bad"}
        header_user, header_tok = MagicMock(), MagicMock()

        with patch.object(auth, "get_validated_token", side_effect=TokenError), patch(
            "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
            return_value=(header_user, header_tok),
        ):
            out = auth.authenticate(request)

        self.assertEqual(out, (header_user, header_tok))

    def test_refresh_cookie_issues_new_access(self):
        auth = CookieJWTAuthentication()
        request = MagicMock()
        request.COOKIES = {"refresh": "ref"}

        with patch(
            "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
            return_value=None,
        ), patch("api.cookie_authentication.RefreshToken") as RT:
            rt_inst = MagicMock()
            rt_inst.access_token = "newacc"
            RT.return_value = rt_inst
            validated = MagicMock()
            user = MagicMock()
            with patch.object(auth, "get_validated_token", return_value=validated), patch.object(
                auth, "get_user", return_value=user
            ):
                out = auth.authenticate(request)

        self.assertEqual(out, (user, validated))
        self.assertEqual(request._new_access_token, "newacc")

    def test_refresh_missing_returns_none(self):
        auth = CookieJWTAuthentication()
        request = MagicMock()
        request.COOKIES = {}

        with patch(
            "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
            return_value=None,
        ):
            self.assertIsNone(auth.authenticate(request))

    def test_refresh_invalid_returns_none(self):
        auth = CookieJWTAuthentication()
        request = MagicMock()
        request.COOKIES = {"refresh": "bad"}

        with patch(
            "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
            return_value=None,
        ), patch("api.cookie_authentication.RefreshToken", side_effect=TokenError):
            self.assertIsNone(auth.authenticate(request))

    def test_authentication_failed_on_cookie_is_swallowed(self):
        auth = CookieJWTAuthentication()
        request = MagicMock()
        request.COOKIES = {"access": "stale"}

        with patch.object(auth, "get_validated_token", side_effect=AuthenticationFailed), patch(
            "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
            return_value=None,
        ):
            self.assertIsNone(auth.authenticate(request))
