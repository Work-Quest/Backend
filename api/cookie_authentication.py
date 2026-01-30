from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.exceptions import AuthenticationFailed

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        access_token = request.COOKIES.get("access")

        if access_token:
            try:
                validated_token = self.get_validated_token(access_token)
                user = self.get_user(validated_token)
                return user, validated_token
            except (InvalidToken, AuthenticationFailed):
                # Important: for endpoints like login/register that are `AllowAny`, we
                # must not fail the whole request just because a stale/invalid cookie
                # is present. Treat as anonymous and allow permissions to decide.
                return None
        
        # Try refresh token
        refresh_token = request.COOKIES.get("refresh")
        if not refresh_token:
            return None
        
        try:
            print("Attempting to refresh access token using refresh token")
            refresh = RefreshToken(refresh_token)
            new_access = str(refresh.access_token)

            validated_token = self.get_validated_token(new_access)
            user = self.get_user(validated_token)

            # Attach new access token to the DRF request object so middleware can set cookie.
            request._new_access_token = new_access

            return user, validated_token

        except (TokenError, InvalidToken, AuthenticationFailed):
            return None