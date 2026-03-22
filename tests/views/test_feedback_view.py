from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from tests.drf_helpers import attach_authenticated_user

from api.models import BusinessUser
from api.views.feedback_view import get_project_feedback


class FeedbackViewTest(SimpleTestCase):
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
