from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from tests.drf_helpers import attach_authenticated_user

from api.models import BusinessUser
from api.views.project_view import create_project


class ProjectViewTest(SimpleTestCase):
    @patch("api.views.project_view.CacheService")
    @patch("api.views.project_view.ProjectSerializer")
    @patch("api.views.project_view.ProjectService")
    @patch.object(BusinessUser.objects, "get")
    def test_create_project_returns_201_when_service_succeeds(
        self, mock_get_bu, mock_ps, mock_ser_cls, _cache
    ):
        mock_get_bu.return_value = MagicMock(user_id="u1")
        domain = MagicMock()
        domain.project = MagicMock()
        mock_ps.return_value.create_project.return_value = domain
        ser = MagicMock()
        ser.data = {"project_id": "p1", "project_name": "P"}
        mock_ser_cls.return_value = ser

        factory = APIRequestFactory()
        request = factory.post(
            "/projects/",
            {"project_name": "P", "deadline": "2027-01-01T00:00:00Z"},
            format="json",
        )
        attach_authenticated_user(request)

        response = create_project(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["project_name"], "P")

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
