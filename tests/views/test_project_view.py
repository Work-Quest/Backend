from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from tests.drf_helpers import attach_authenticated_user

from api.models import BusinessUser
from api.views.project_view import create_project


class ProjectViewTest(SimpleTestCase):
    def test_create_project_returns_400_when_business_user_missing(self):
        factory = APIRequestFactory()
        request = factory.post(
            "/projects/",
            {"project_name": "P", "deadline": None},
            format="json",
        )
        attach_authenticated_user(request)

        with patch.object(
            BusinessUser.objects,
            "get",
            side_effect=BusinessUser.DoesNotExist,
        ):
            response = create_project(request)

        self.assertEqual(response.status_code, 400)
