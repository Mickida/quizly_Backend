from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

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


def delete_token_cookies(response):
    """Remove both JWT cookies from the client."""
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(name, samesite='Lax')


def blacklist_refresh_token(raw_token):
    """Blacklist a refresh token; missing or invalid tokens are skipped.

    An invalid token cannot be used anymore anyway, so the logout
    succeeds in every case.
    """
    if not raw_token:
        return
    try:
        RefreshToken(raw_token).blacklist()
    except TokenError:
        return
