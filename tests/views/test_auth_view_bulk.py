from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from tests.drf_helpers import attach_authenticated_user

from api.models import BusinessUser
from api.views import auth_view as auth_view_module
from api.views.auth_view import (
    check_auth_status,
    google_login,
    login,
    logout,
    refresh_token,
    register,
)


class AuthViewBulkTest(SimpleTestCase):
    def test_register_missing_fields_400(self):
        req = APIRequestFactory().post("/r", {}, format="json")
        resp = register(req)
        self.assertEqual(resp.status_code, 400)

    @patch.object(BusinessUser.objects, "filter")
    @patch("api.views.auth_view.register_user")
    def test_register_username_taken(self, _reg, mock_filter):
        mock_filter.return_value.exists.return_value = True
        req = APIRequestFactory().post(
            "/r",
            {"username": "u", "password": "p", "email": "e@e.com"},
            format="json",
        )
        resp = register(req)
        self.assertEqual(resp.status_code, 400)

    @patch("api.views.auth_view.BusinessUser.objects.filter")
    @patch("api.views.auth_view.register_user")
    @patch("api.views.auth_view.CacheService")
    def test_register_success(self, _cache, mock_register, mock_filter):
        mock_filter.return_value.exists.return_value = False
        u = MagicMock(username="u")
        p = MagicMock(email="e@e.com")
        mock_register.return_value = (u, p)
        req = APIRequestFactory().post(
            "/r",
            {"username": "u", "password": "p", "email": "e@e.com"},
            format="json",
        )
        resp = register(req)
        self.assertEqual(resp.status_code, 200)

    @patch("api.views.auth_view.BusinessUser.objects.get")
    def test_login_invalid_email(self, mock_get):
        mock_get.side_effect = BusinessUser.DoesNotExist
        req = APIRequestFactory().post(
            "/l", {"email": "x@x.com", "password": "p"}, format="json"
        )
        resp = login(req)
        self.assertEqual(resp.status_code, 401)

    @patch("api.views.auth_view.login_user")
    @patch("api.views.auth_view.BusinessUser.objects.get")
    def test_login_invalid_password(self, mock_get, mock_login):
        mock_get.return_value = MagicMock(username="u")
        mock_login.return_value = (None, None)
        req = APIRequestFactory().post(
            "/l", {"email": "e@e.com", "password": "bad"}, format="json"
        )
        resp = login(req)
        self.assertEqual(resp.status_code, 401)

    def test_logout_clears_cookies(self):
        req = APIRequestFactory().post("/out", {}, format="json")
        attach_authenticated_user(req)
        resp = logout(req)
        self.assertEqual(resp.status_code, 200)

    def test_check_auth_authenticated(self):
        req = APIRequestFactory().get("/check")
        attach_authenticated_user(req)
        resp = check_auth_status(req)
        self.assertTrue(resp.data["isAuthenticated"])

    def test_check_auth_anonymous(self):
        req = APIRequestFactory().get("/check")
        req.user = AnonymousUser()
        resp = check_auth_status(req)
        self.assertFalse(resp.data["isAuthenticated"])

    def test_google_login_missing_token(self):
        req = APIRequestFactory().post("/g", {}, format="json")
        resp = google_login(req)
        self.assertEqual(resp.status_code, 400)

    @patch("api.views.auth_view.requests.get")
    def test_google_login_no_email_in_profile(self, mock_get):
        # Empty email hits `if not email` after building display name (avoid None.split bug).
        mock_get.return_value.json.return_value = {"email": "", "name": "x"}
        req = APIRequestFactory().post(
            "/g", {"access_token": "tok"}, format="json"
        )
        resp = google_login(req)
        self.assertEqual(resp.status_code, 400)

    @patch("api.views.auth_view.login_user")
    @patch("api.views.auth_view.CacheService")
    @patch("api.views.auth_view.register_user")
    @patch("api.views.auth_view.BusinessUser.objects.get")
    @patch("api.views.auth_view.requests.get")
    def test_google_login_new_user_registers(
        self, mock_http, mock_bu_get, mock_register, _cache, mock_login
    ):
        mock_http.return_value.json.return_value = {
            "email": "g@g.com",
            "name": "G",
            "picture": "http://p",
        }
        mock_bu_get.side_effect = BusinessUser.DoesNotExist
        bu = MagicMock(username="g")
        mock_register.return_value = (bu, MagicMock())
        mock_login.return_value = (bu, {"access": "a", "refresh": "r"})
        req = APIRequestFactory().post(
            "/g", {"access_token": "tok"}, format="json"
        )
        resp = google_login(req)
        self.assertEqual(resp.status_code, 200)

    @patch("api.views.auth_view.login_user")
    @patch("api.views.auth_view.BusinessUser.objects.get")
    @patch("api.views.auth_view.requests.get")
    def test_google_login_existing_user(
        self, mock_http, mock_bu_get, mock_login
    ):
        mock_http.return_value.json.return_value = {"email": "g@g.com"}
        bu = MagicMock(username="g")
        mock_bu_get.return_value = bu
        mock_login.return_value = (bu, {"access": "a", "refresh": "r"})
        req = APIRequestFactory().post(
            "/g", {"access_token": "tok"}, format="json"
        )
        resp = google_login(req)
        self.assertEqual(resp.status_code, 200)

    def test_refresh_missing_token(self):
        req = APIRequestFactory().post("/ref", {}, format="json")
        resp = refresh_token(req)
        self.assertEqual(resp.status_code, 401)

    @patch.object(auth_view_module, "RefreshToken", side_effect=Exception("bad"))
    def test_refresh_invalid(self, _rt):
        req = APIRequestFactory().post(
            "/ref", {"refresh": "x"}, format="json"
        )
        resp = refresh_token(req)
        self.assertEqual(resp.status_code, 401)

    @patch.object(auth_view_module, "RefreshToken")
    def test_refresh_ok(self, mock_rt_cls):
        rt = MagicMock()
        rt.access_token = "at"
        mock_rt_cls.return_value = rt
        req = APIRequestFactory().post(
            "/ref", {"refresh": "good"}, format="json"
        )
        resp = refresh_token(req)
        self.assertEqual(resp.status_code, 200)
