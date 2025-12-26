
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.services.auth_service import register_user, login_user
from rest_framework import status
from api.models import BusinessUser


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    userData = BusinessUser.objects.get(username=user.username)
    return Response({
        "id": userData.user_id,
        "username": userData.username,
        "name": userData.name,
        "email": userData.email,
        "profile_img" : userData.profile_img
    })