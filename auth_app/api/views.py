from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.api.serializers import RegistrationSerializer


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
