from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from api.services.auth_service import register_user, login_user
from rest_framework import status
from api.models import BusinessUser
from api.services.cache_service import CacheService
import requests
import uuid
from django.conf import settings


def _cookie_kwargs() -> dict:
    """
    Centralize cookie attributes so login/refresh/middleware stay consistent.

    Notes:
    - Cross-site (different base domains): SameSite=None AND Secure=True are required by browsers.
    - Same-site (recommended): SameSite=Lax is typically fine.
    """
    kwargs = {
        "httponly": True,
        "secure": getattr(settings, "DJANGO_COOKIE_SECURE", False),
        "samesite": getattr(settings, "DJANGO_COOKIE_SAMESITE", "Lax"),
        "path": "/",
    }
    domain = getattr(settings, "DJANGO_COOKIE_DOMAIN", None)
    if domain:
        kwargs["domain"] = domain
    return kwargs

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

    # New user changes the global business user list cache.
    CacheService().invalidate_all_business_users()

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
        {
            "username": user.username,
            # Also returned for clients where cross-site HTTP-only cookies are blocked (e.g. Safari).
            "access": tokens["access"],
            "refresh": tokens["refresh"],
        },
        status=status.HTTP_200_OK,
    )

    cookie_kwargs = _cookie_kwargs()

    # HTTP-Only Access Token
    response.set_cookie(
        key="access",
        value=tokens["access"],
        max_age=60 * 60 * 24 * 3,  # 3 day
        **cookie_kwargs,
    )

    # HTTP-Only Refresh Token 
    response.set_cookie(
        key="refresh",
        value=tokens["refresh"],
        max_age=60 * 60 * 24 * 7,  # 7 days
        **cookie_kwargs,
    )

    return response

@api_view(["POST"])
@permission_classes([IsAuthenticated])  
def logout(request):
    response = Response({"message": "Logged out"})
    cookie_kwargs = _cookie_kwargs()
    response.delete_cookie("access", path=cookie_kwargs.get("path", "/"), domain=cookie_kwargs.get("domain"))
    response.delete_cookie("refresh", path=cookie_kwargs.get("path", "/"), domain=cookie_kwargs.get("domain"))
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
        # New user changes the global business user list cache.
        CacheService().invalidate_all_business_users()

    # Log the user in via your login service
    user, tokens = login_user(
        username=user.username,
        password=None,
        social=True        
    )

    # Issue cookies + body tokens for Bearer fallback (Safari / cross-site)
    response = Response(
        {
            "username": user.username,
            "access": tokens["access"],
            "refresh": tokens["refresh"],
        }
    )

    cookie_kwargs = _cookie_kwargs()

   # HTTP-Only Access Token
    response.set_cookie(
        key="access",
        value=tokens["access"],
        max_age=60*60,
        **cookie_kwargs,
    )

    # HTTP-Only Refresh Token 
    response.set_cookie(
        key="refresh",
        value=tokens["refresh"],
        max_age=60 * 60 * 24 * 3,  # 3 days
        **cookie_kwargs,
    )

    return response


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token(request):
    refresh_token = request.COOKIES.get("refresh") or request.data.get("refresh")

    if not refresh_token:
        return Response({"error": "No refresh token"}, status=401)

    try:
        refresh = RefreshToken(refresh_token)
        access = str(refresh.access_token)
    except Exception:
        return Response({"error": "Invalid refresh token"}, status=401)

    response = Response(
        {
            "message": "Token refreshed",
            "access": access,
        }
    )
    cookie_kwargs = _cookie_kwargs()
    response.set_cookie(
        key="access",
        value=access,
        max_age=60*60,
        **cookie_kwargs,
    )
    return response
