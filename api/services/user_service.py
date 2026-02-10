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
            }
            for u in users
        ]


