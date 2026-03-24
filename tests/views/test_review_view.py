from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from tests.drf_helpers import attach_authenticated_user

from api.views.review_view import review_report


class ReviewViewTest(SimpleTestCase):
    @patch("api.views.review_view.CacheService")
    @patch("api.views.review_view.UserReportResponseSerializer")
    @patch("api.views.review_view.ReviewService")
    @patch("api.views.review_view.BusinessUser.objects.get")
    def test_review_report_returns_201_when_create_succeeds(
        self, mock_get_bu, mock_review_svc, mock_ser_cls, _mock_cache
    ):
        mock_get_bu.return_value = MagicMock()
        mock_review_svc.return_value.create_review_report.return_value = (
            MagicMock(),
            [MagicMock()],
        )
        ser = MagicMock()
        ser.data = [{"user_report_id": "ur1"}]
        mock_ser_cls.return_value = ser

        factory = APIRequestFactory()
        request = factory.post(
            "/review/",
            {"task_id": "t", "description": "Solid work"},
            format="json",
        )
        attach_authenticated_user(request)

        response = review_report(request, project_id="pid")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data, [{"user_report_id": "ur1"}])

    @patch("api.views.review_view.CacheService")
    @patch("api.views.review_view.ReviewService")
    @patch("api.views.review_view.BusinessUser.objects.get")
    def test_review_report_returns_400_on_value_error(
        self, mock_get_bu, mock_review_svc, _mock_cache
    ):
        mock_get_bu.return_value = MagicMock()
        mock_review_svc.return_value.create_review_report.side_effect = ValueError(
            "bad payload"
        )

        factory = APIRequestFactory()
        request = factory.post(
            "/review/",
            {"task_id": "t", "description": "x"},
            format="json",
        )
        attach_authenticated_user(request)

        response = review_report(request, project_id="pid")

        self.assertEqual(response.status_code, 400)
