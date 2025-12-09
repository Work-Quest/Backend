from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from api.services.auth_service import register_user, login_user
from rest_framework import status
from api.models import BusinessUser

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    data = request.data
   
    # Required fields
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    
    if not username or not password or not email:
        return Response(
            {"error": "username and password are required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # check if already have username or email
    if BusinessUser.objects.filter(username=username).exists():
        return Response(
            {"error": "Username already exists"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if email and BusinessUser.objects.filter(email=email).exists():
        return Response(
            {"error": "Email already exists"},
            status=status.HTTP_400_BAD_REQUEST
        )


    user, profile = register_user(
        username=data["username"],
        email=data["email"],
        password=data["password"],
        name=data["username"],
        profile_img=None,
    )

    return Response({"message": "User registered", "username": user.username, "email" : profile.email})


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    data = request.data

    try:
        username = BusinessUser.objects.get(email=data.get("email")).username
    except BusinessUser.DoesNotExist:
        return Response({"error": "Invalid credentials"}, status=401)


    user, tokens = login_user(
        username=username,
        password=data["password"],
    )

    if not user:
        return Response({"error": "Invalid credentials"}, status=401)

    response = Response(
        {"username": user.username},
        status=status.HTTP_200_OK
    )

    # HTTP-Only Access Token
    response.set_cookie(
        key="access",
        value=tokens["access"],
        httponly=True,
        secure=False,     # TODO: True in production (HTTPS)
        samesite="Lax",
        max_age=60 * 60 * 24 * 3,  # 3 day
    )

    # HTTP-Only Refresh Token 
    response.set_cookie(
        key="refresh",
        value=tokens["refresh"],
        httponly=True,
        secure=False, # TODO: True in production (HTTPS)
        samesite="Lax",
        max_age=60 * 60 * 24 * 7,  # 7 days
    )

    return response

@api_view(["GET"])
@permission_classes([AllowAny])  
def check_auth_status(request):
    if request.user.is_authenticated:
        return Response({
            "isAuthenticated": True
        })

    return Response({
        "isAuthenticated": False
    })