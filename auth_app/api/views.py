from django.contrib.auth import authenticate
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from auth_app.api.serializers import (
    LoginSerializer,
    RegistrationSerializer,
    UserSerializer,
)
from auth_app.utils import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    blacklist_refresh_token,
    delete_token_cookies,
    set_token_cookie,
)

# Errors meaning the refresh cookie is missing, invalid, blacklisted or
# belongs to a user who was deleted or deactivated.
REFRESH_ERRORS = (
    TokenError,
    ValidationError,
    AuthenticationFailed,
    ObjectDoesNotExist,
)


class RegistrationView(APIView):
    """Register a new user account."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Create a user from the submitted sign-up data."""
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'detail': 'User created successfully!'},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Log a user in and set the JWT cookies."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Validate the credentials and return the user data."""
        serializer = LoginSerializer(data=request.data)
        user = None
        if serializer.is_valid():
            user = authenticate(**serializer.validated_data)
        if user is None:
            return Response(
                {'detail': 'Invalid username or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return self.build_login_response(user)

    def build_login_response(self, user):
        """Return the success response with both token cookies set."""
        refresh = RefreshToken.for_user(user)
        response = Response({
            'detail': 'Login successfully!',
            'user': UserSerializer(user).data,
        })
        set_token_cookie(response, ACCESS_COOKIE, refresh.access_token)
        set_token_cookie(response, REFRESH_COOKIE, refresh)
        return response


class CookieTokenRefreshView(APIView):
    """Issue a new access token from the refresh_token cookie."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Validate the refresh cookie and set a new access cookie."""
        access = self.get_new_access_token(request)
        if access is None:
            return Response(
                {'detail': 'Refresh token invalid or missing.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        response = Response({'detail': 'Token refreshed'})
        set_token_cookie(response, ACCESS_COOKIE, access)
        return response

    def get_new_access_token(self, request):
        """Return a new access token from the refresh cookie, or None."""
        serializer = TokenRefreshSerializer(
            data={'refresh': request.COOKIES.get(REFRESH_COOKIE)}
        )
        try:
            serializer.is_valid(raise_exception=True)
        except REFRESH_ERRORS:
            return None
        return serializer.validated_data['access']


class LogoutView(APIView):
    """Log the user out and invalidate the refresh token."""

    def post(self, request):
        """Blacklist the refresh token and delete both cookies."""
        blacklist_refresh_token(request.COOKIES.get(REFRESH_COOKIE))
        response = Response({
            'detail': 'Log-Out successfully! All Tokens will be deleted. '
                      'Refresh token is now invalid.'
        })
        delete_token_cookies(response)
        return response
