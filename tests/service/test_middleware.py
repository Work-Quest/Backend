import os
from unittest.mock import MagicMock, patch

from django.http import HttpResponse, JsonResponse
from django.test import SimpleTestCase, override_settings

from api.middleware import InternalAPIKeyMiddleware, RefreshTokenMiddleware


class RefreshTokenMiddlewareTest(SimpleTestCase):
    @override_settings(
        DJANGO_COOKIE_SAMESITE="Strict",
        DJANGO_COOKIE_SECURE=True,
        DJANGO_COOKIE_DOMAIN=".example.com",
    )
    def test_sets_access_cookie_when_token_attached(self):
        inner = MagicMock(return_value=HttpResponse("ok"))
        mw = RefreshTokenMiddleware(inner)
        request = MagicMock()
        request._new_access_token = "fresh"

        response = mw(request)

        inner.assert_called_once_with(request)
        self.assertEqual(response.cookies["access"].value, "fresh")
        self.assertTrue(response.cookies["access"]["httponly"])

    def test_no_token_passes_through(self):
        inner = MagicMock(return_value=HttpResponse("ok"))
        mw = RefreshTokenMiddleware(inner)
        request = MagicMock(spec=[])  # no _new_access_token

        response = mw(request)

        inner.assert_called_once_with(request)
        self.assertEqual(response.content, b"ok")


class InternalAPIKeyMiddlewareTest(SimpleTestCase):
    @patch.dict(os.environ, {"INTERNAL_SERVICE_API_KEY": "secret"}, clear=False)
    @patch("api.middleware.print")
    def test_allows_non_internal_paths(self, _print):
        inner = MagicMock(return_value=HttpResponse("x"))
        mw = InternalAPIKeyMiddleware(inner)
        request = MagicMock()
        request.path = "/api/projects/"
        request.headers = {}

        response = mw(request)

        self.assertEqual(response.content, b"x")
        inner.assert_called_once_with(request)

    @patch.dict(os.environ, {"INTERNAL_SERVICE_API_KEY": "secret"}, clear=False)
    @patch("api.middleware.print")
    def test_internal_path_blocks_without_key(self, _print):
        inner = MagicMock()
        mw = InternalAPIKeyMiddleware(inner)
        request = MagicMock()
        request.path = "/api/internal/jobs"
        request.headers = {}

        response = mw(request)

        inner.assert_not_called()
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 403)

    @patch.dict(os.environ, {"INTERNAL_SERVICE_API_KEY": "good"}, clear=False)
    @patch("api.middleware.print")
    def test_internal_path_allows_valid_key(self, _print):
        inner = MagicMock(return_value=HttpResponse("y"))
        mw = InternalAPIKeyMiddleware(inner)
        request = MagicMock()
        request.path = "/api/internal/x"
        request.headers = {"X-API-KEY": "good"}

        response = mw(request)

        inner.assert_called_once_with(request)
        self.assertEqual(response.content, b"y")
