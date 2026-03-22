from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from tests.drf_helpers import attach_authenticated_user

from api.views.user_view import get_all_business_users


class UserViewTest(SimpleTestCase):
    @patch("api.views.user_view.CacheService")
    def test_get_all_business_users_returns_cached_payload(self, mock_cache_cls):
        mock_cache = MagicMock()
        mock_cache.keys.all_business_users.return_value = "k"
        mock_cache.read_through.return_value = [{"id": 1}]
        mock_cache_cls.return_value = mock_cache

        factory = APIRequestFactory()
        request = factory.get("/users/")
        attach_authenticated_user(request)

        response = get_all_business_users(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [{"id": 1}])
