from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from api.services.cache_service import CacheService
from api.services.user_service import UserService


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_all_business_users(request):
    """
    Get all business users existing in the database.
    """
    cache_svc = CacheService()

    data = cache_svc.read_through(
        key=cache_svc.keys.all_business_users(),
        ttl_seconds=60,
        loader=UserService().get_all_business_users,
    )

    return Response(data, status=status.HTTP_200_OK)


