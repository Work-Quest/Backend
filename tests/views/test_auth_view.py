from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from api.views.auth_view import _cookie_kwargs, register


class AuthViewTest(SimpleTestCase):
    def test_register_returns_400_when_fields_missing(self):
        factory = APIRequestFactory()
        request = factory.post("/register", {}, format="json")

        response = register(request)

        self.assertEqual(response.status_code, 400)

    def test_cookie_kwargs_includes_expected_keys(self):
        kwargs = _cookie_kwargs()
        self.assertTrue(kwargs["httponly"])
        self.assertEqual(kwargs["path"], "/")
