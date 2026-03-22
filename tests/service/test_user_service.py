from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api.services.user_service import UserService


class UserServiceTest(SimpleTestCase):
    @patch("api.services.user_service.BusinessUser.objects")
    def test_get_all_business_users_maps_fields(self, mock_mgr):
        u = MagicMock()
        u.user_id = 1
        u.username = "u"
        u.name = "N"
        u.email = "e@e.com"
        u.profile_img = None
        u.selected_character_id = 1
        u.bg_color_id = 2
        u.is_first_time = True
        mock_mgr.all.return_value.order_by.return_value = [u]

        rows = UserService().get_all_business_users()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["username"], "u")
