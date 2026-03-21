from __future__ import annotations

from api.models import BusinessUser


class UserService:
    def get_all_business_users(self) -> list[dict]:
        users = BusinessUser.objects.all().order_by("username")
        return [
            {
                "id": u.user_id,
                "username": u.username,
                "name": u.name,
                "email": u.email,
                "profile_img": u.profile_img,
                "selected_character_id": u.selected_character_id,
                "bg_color_id": u.bg_color_id,
                "is_first_time": u.is_first_time,
            }
            for u in users
        ]


