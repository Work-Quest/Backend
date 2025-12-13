from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        access_token = request.COOKIES.get("access")

        if access_token:
            try:
                validated_token = self.get_validated_token(access_token)
                return self.get_user(validated_token), validated_token
            except InvalidToken:
                print ("Access token invalid or expired")
                pass
        
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

            # attach new access token to request
            request._request._new_access_token = new_access

            print(request._request._new_access_token)

            return user, validated_token

        except TokenError:
            return None


        return self.get_user(validated_token), validated_token