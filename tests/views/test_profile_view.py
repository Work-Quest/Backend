from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from tests.drf_helpers import attach_authenticated_user

from api.views.profile_view import (
    get_user_defeated_bosses,
    get_user_finished_projects,
    get_user_profile_stats,
    me,
    me_achievements,
)


class ProfileViewTest(SimpleTestCase):
    @patch("api.views.profile_view.CacheService")
    @patch("api.views.profile_view.BusinessUser.objects.get")
    def test_me_get_returns_payload_from_cache(self, mock_get_bu, mock_cache_cls):
        mock_get_bu.return_value = MagicMock(
            user_id=1,
            username="u",
            name="n",
            email="e@e.com",
            profile_img=None,
            selected_character_id=1,
            bg_color_id=1,
            is_first_time=False,
        )
        mock_cache = MagicMock()
        mock_cache.read_through.return_value = {"username": "u"}
        mock_cache_cls.return_value = mock_cache

        factory = APIRequestFactory()
        request = factory.get("/me/")
        attach_authenticated_user(request, username="u", pk=1)

        response = me(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"username": "u"})

    @patch("api.views.profile_view.CacheService")
    @patch("api.views.profile_view.BusinessUser.objects.get")
    def test_me_patch_empty_returns_400(self, mock_get_bu, _mock_cache_cls):
        mock_get_bu.return_value = MagicMock(is_first_time=True)

        factory = APIRequestFactory()
        request = factory.patch("/me/", {}, format="json")
        attach_authenticated_user(request, username="u", pk=1)

        response = me(request)

        self.assertEqual(response.status_code, 400)

    @patch("api.views.profile_view.ProjectMember.objects.filter")
    @patch("api.views.profile_view.CacheService")
    @patch("api.views.profile_view.BusinessUser.objects.get")
    def test_me_patch_updates_name(self, mock_get_bu, mock_cache_cls, mock_pm_filter):
        user_row = MagicMock(
            user_id=1,
            username="u",
            name="old",
            email="e@e.com",
            profile_img=None,
            selected_character_id=1,
            bg_color_id=1,
            is_first_time=False,
            auth_user=MagicMock(),
            save=MagicMock(),
        )
        mock_get_bu.return_value = user_row
        mock_pm_filter.return_value.values_list.return_value = []
        cache = MagicMock()
        mock_cache_cls.return_value = cache

        factory = APIRequestFactory()
        request = factory.patch("/me/", {"name": "  New Name  "}, format="json")
        attach_authenticated_user(request, username="u", pk=1)

        response = me(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(user_row.name, "New Name")

    @patch("api.views.profile_view.ProjectService")
    @patch("api.views.profile_view.BusinessUser.objects.get")
    def test_get_user_finished_projects_with_user_id(self, mock_get, mock_ps):
        mock_get.return_value = MagicMock()
        mock_ps.return_value.get_user_finished_projects.return_value = []
        factory = APIRequestFactory()
        request = factory.get("/finished/?user_id=abc")
        attach_authenticated_user(request)
        self.assertEqual(get_user_finished_projects(request).status_code, 200)

    @patch("api.views.profile_view.ProjectService")
    @patch("api.views.profile_view.BusinessUser.objects.get")
    def test_get_user_finished_projects_current_user(self, mock_get, mock_ps):
        mock_get.return_value = MagicMock()
        mock_ps.return_value.get_user_finished_projects.return_value = []
        factory = APIRequestFactory()
        request = factory.get("/finished/")
        attach_authenticated_user(request)
        self.assertEqual(get_user_finished_projects(request).status_code, 200)

    @patch("api.views.profile_view.ProjectService")
    @patch("api.views.profile_view.BusinessUser.objects.get")
    def test_get_user_profile_stats(self, mock_get, mock_ps):
        mock_get.return_value = MagicMock()
        mock_ps.return_value.get_user_profile_stats.return_value = {"s": 1}
        factory = APIRequestFactory()
        request = factory.get("/stats/?user_id=x")
        attach_authenticated_user(request)
        self.assertEqual(get_user_profile_stats(request).status_code, 200)

    @patch("api.views.profile_view.ProjectService")
    @patch("api.views.profile_view.BusinessUser.objects.get")
    def test_get_user_defeated_bosses(self, mock_get, mock_ps):
        mock_get.return_value = MagicMock()
        mock_ps.return_value.get_user_defeated_bosses.return_value = []
        factory = APIRequestFactory()
        request = factory.get("/bosses/")
        attach_authenticated_user(request)
        self.assertEqual(get_user_defeated_bosses(request).status_code, 200)

    @patch("api.views.profile_view.get_overall_achievement_ids_for_user", return_value=["01"])
    @patch("api.views.profile_view.BusinessUser.objects.get")
    def test_me_achievements(self, _mock_bu, _mock_ach):
        factory = APIRequestFactory()
        request = factory.get("/me/achievements/")
        attach_authenticated_user(request)
        r = me_achievements(request)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["achievement_ids"], ["01"])
