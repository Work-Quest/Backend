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
                samesite="Lax",
                secure=False,  # TODO: True in prod
                max_age=60*60,
            )

        return response
