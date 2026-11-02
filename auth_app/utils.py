ACCESS_COOKIE = 'access_token'
REFRESH_COOKIE = 'refresh_token'


def set_token_cookie(response, name, token):
    """Attach a JWT to the response as an HttpOnly cookie."""
    response.set_cookie(
        key=name,
        value=str(token),
        httponly=True,
        secure=False,
        samesite='Lax',
    )
