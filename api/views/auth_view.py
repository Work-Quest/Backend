from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from api.services.auth_service import register_user, login_user
from rest_framework import status
from api.models import BusinessUser
import requests
import uuid

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

@api_view(["POST"])
@permission_classes([IsAuthenticated])  
def logout(request):
    response = Response({"message": "Logged out"})
    response.delete_cookie("access")
    response.delete_cookie("refresh")
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


@api_view(["POST"])
@permission_classes([AllowAny])
def google_login(request):
    access_token = request.data.get("access_token")

    if not access_token:
        return Response({"error": "Missing access_token"}, status=400)

    # Get Google user info
    google_res = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    email = google_res.get("email")
    name = google_res.get("name") or email.split("@")[0]
    picture = google_res.get("picture")  # optional — save profile image

    if not email:
        return Response({"error": "Google auth failed"}, status=400)

    # If user does not exist register using your service

    random_password = uuid.uuid4().hex
    try:
        user = BusinessUser.objects.get(email=email)
    except BusinessUser.DoesNotExist:
        # Use your existing register service
        user, profile = register_user(
            username=email.split("@")[0],
            email=email,
            password=random_password,        
            name=name,
            profile_img=picture,
        )

    # Log the user in via your login service
    user, tokens = login_user(
        username=user.username,
        password=None,
        social=True        
    )

    # Issue cookies
    response = Response({"username": user.username})

   # HTTP-Only Access Token
    response.set_cookie(
        key="access",
        value=tokens["access"],
        httponly=True,
        samesite="lax",
        secure=False,     # TODO: True in production (HTTPS)
        max_age=60*60
    )

    # HTTP-Only Refresh Token 
    response.set_cookie(
        key="refresh",
        value=tokens["refresh"],
        httponly=True,
        samesite="lax",
        secure=False, # TODO: True in production (HTTPS)
        max_age=60 * 60 * 24 * 3,  # 3 days
    )

    return response


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token(request):
    refresh_token = request.COOKIES.get("refresh")

    if not refresh_token:
        return Response({"error": "No refresh token"}, status=401)

    try:
        refresh = RefreshToken(refresh_token)
        access = str(refresh.access_token)
    except Exception:
        return Response({"error": "Invalid refresh token"}, status=401)

    response = Response({"message": "Token refreshed"})
    response.set_cookie(
        key="access",
        value=access,
        httponly=True,
        samesite="Lax",
        secure=False,  # TODO: True in prod
        max_age=60*60
    )
    return response
