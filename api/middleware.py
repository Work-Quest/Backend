import os

from django.http import JsonResponse
from django.conf import settings
class RefreshTokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        new_access = getattr(request, "_new_access_token", None)
        if new_access:
            print("Setting new access token cookie in response")
            response.set_cookie(
                key="access",
                value=new_access,
                httponly=True,
                samesite=getattr(settings, "DJANGO_COOKIE_SAMESITE", "Lax"),
                secure=getattr(settings, "DJANGO_COOKIE_SECURE", False),
                domain=getattr(settings, "DJANGO_COOKIE_DOMAIN", None),
                path="/",
                max_age=60*60,
            )

        return response
class InternalAPIKeyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Protect only internal endpoints
        if request.path.startswith("/api/internal/"):
            api_key = request.headers.get("X-API-KEY")
            print(f"InternalAPIKeyMiddleware: Received API key: {api_key}")
            if not api_key or api_key != os.getenv("INTERNAL_SERVICE_API_KEY"):
                print("InternalAPIKeyMiddleware: Invalid or missing API key")
                return JsonResponse(
                    {"detail": "Invalid or missing API key"},
                    status=403
                )
        print("InternalAPIKeyMiddleware: API key valid, proceeding to view")
        return self.get_response(request)