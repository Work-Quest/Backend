from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import BusinessUser
from api.services.cache_service import CacheService
from api.services.achievement_service import get_overall_achievement_ids_for_user


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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_achievements(request):
    """
    GET /me/achievements/

    Returns overall achievement IDs the authenticated user has unlocked
    across all projects (for profile page).
    """
    try:
        user = request.user
        business_user = BusinessUser.objects.get(auth_user=user)
        achievement_ids = get_overall_achievement_ids_for_user(business_user)
        return Response({"achievement_ids": achievement_ids}, status=status.HTTP_200_OK)
    except BusinessUser.DoesNotExist:
        return Response(
            {"error": "Business user profile not found"},
            status=status.HTTP_400_BAD_REQUEST,
        )