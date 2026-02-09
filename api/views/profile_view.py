
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.services.auth_service import register_user, login_user
from rest_framework import status
from api.models import BusinessUser
from api.services.cache_service import CacheService


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    cache_svc = CacheService()

    def _load():
        userData = BusinessUser.objects.get(username=user.username)
        return {
            "id": userData.user_id,
            "username": userData.username,
            "name": userData.name,
            "email": userData.email,
            "profile_img": userData.profile_img,
        }

    data = cache_svc.read_through(
        key=cache_svc.keys.user_me(user.id),
        ttl_seconds=30,
        loader=_load,
    )
    return Response(data)