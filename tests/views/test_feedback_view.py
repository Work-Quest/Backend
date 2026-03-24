from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from tests.drf_helpers import attach_authenticated_user

from api.models import BusinessUser
from api.views.feedback_view import get_project_feedback


class FeedbackViewTest(SimpleTestCase):
    @patch("api.views.feedback_view.UserFeedbackSerializer")
    @patch("api.views.feedback_view.feedbackService")
    @patch("api.views.feedback_view.ProjectMember.objects.get")
    @patch.object(BusinessUser.objects, "get")
    def test_get_project_feedback_returns_200_when_member_and_feedback_loads(
        self, mock_bu_get, mock_pm_get, mock_fb_factory, mock_ser_cls
    ):
        mock_bu_get.return_value = MagicMock()
        mock_pm_get.return_value = MagicMock(project_member_id="m1")
        mock_fb_factory.return_value.get_feedback.return_value = MagicMock()
        ser = MagicMock()
        ser.data = {"achievement_ids": [], "feedback": "ok"}
        mock_ser_cls.return_value = ser

        factory = APIRequestFactory()
        request = factory.get("/feedback/")
        attach_authenticated_user(request)

        response = get_project_feedback(request, project_id="pid")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["feedback"], "ok")

    def test_get_project_feedback_400_when_business_user_missing(self):
        factory = APIRequestFactory()
        request = factory.get("/feedback/")
        attach_authenticated_user(request)

        with patch.object(
            BusinessUser.objects,
            "get",
            side_effect=BusinessUser.DoesNotExist,
        ):
            response = get_project_feedback(request, project_id="pid")

        self.assertEqual(response.status_code, 400)
