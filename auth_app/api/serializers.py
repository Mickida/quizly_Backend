from django.contrib.auth.models import User
from rest_framework import serializers


class RegistrationSerializer(serializers.ModelSerializer):
    """Validate sign-up data and create a new user account."""

    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirmed_password']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True, 'allow_blank': False},
        }

    def validate_email(self, value):
        """Normalize the email and reject one that is already in use."""
        email = value.lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Email is already in use.')
        return email

    def validate(self, attrs):
        """Ensure both password fields match."""
        if attrs['password'] != attrs['confirmed_password']:
            raise serializers.ValidationError(
                {'confirmed_password': 'Passwords do not match.'}
            )
        return attrs

    def create(self, validated_data):
        """Create the user with a hashed password."""
        validated_data.pop('confirmed_password')
        return User.objects.create_user(**validated_data)
