from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from auth_app.api.serializers import (
    LoginSerializer,
    RegistrationSerializer,
    UserSerializer,
)
from auth_app.utils import ACCESS_COOKIE, REFRESH_COOKIE, set_token_cookie


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
