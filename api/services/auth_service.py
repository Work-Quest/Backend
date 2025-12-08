from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from api.models import BusinessUser


def register_user(username, email, password, name, profile_img):
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )

    business_user = BusinessUser.objects.create(
        auth_user=user,
        username=username,
        email=email,
        name=name,
        profile_img=profile_img,
    )

    return user, business_user


def login_user(username, password):
    user = authenticate(username=username, password=password)
    if not user:
        return None, None

    refresh = RefreshToken.for_user(user)

    return user, {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }
