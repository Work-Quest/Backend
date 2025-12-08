from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from yourapp.services.auth_service import register_user, login_user


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    data = request.data

    user, profile = register_user(
        username=data["username"],
        email=data["email"],
        password=data["password"],
        name=data["name"],
        profile_img=data["profile_img"],
    )

    return Response({"message": "User registered"})


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    data = request.data

    user, tokens = login_user(
        username=data["username"],
        password=data["password"],
    )

    if not user:
        return Response({"error": "Invalid credentials"}, status=401)

    return Response({
        "access": tokens["access"],
        "refresh": tokens["refresh"],
    })
