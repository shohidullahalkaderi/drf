<<<<<<< HEAD
import secrets
from django.core.cache import cache
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
=======
import re
from django.contrib.auth import authenticate, get_user_model
>>>>>>> 55e1008 (updated password validation to prevent brute force and dictionary attack.)
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

<<<<<<< HEAD
TOKEN_EXPIRY_SECONDS = 86400  # 24 Hours
USER_CACHE_EXPIRY_SECONDS = 3600  # 1 Hour

class TokenManager:
    @staticmethod
    def generate_token() -> str:
        return secrets.token_hex(20)

    @staticmethod
    def create_session(user_id: int) -> str:
        token = TokenManager.generate_token()
        cache.set(f"auth_token_{token}", user_id, TOKEN_EXPIRY_SECONDS)
        return token

    @staticmethod
    def get_user_id(token: str) -> int:
        return cache.get(f"auth_token_{token}")

    @staticmethod
    def destroy_session(token: str) -> None:
        cache.delete(f"auth_token_{token}")
        
    @staticmethod
    def clear_cached_user(user_id: int) -> None:
        cache.delete(f"user_profile_{user_id}")

=======
User = get_user_model()
>>>>>>> 55e1008 (updated password validation to prevent brute force and dictionary attack.)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')


class RegisterSerializer(serializers.ModelSerializer):
    # Enforce standard constraints matching your architectural requirements
    username = serializers.CharField(
        min_length=3,
        max_length=50,
        required=True
    )
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'}
    )
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    last_name = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'first_name', 'last_name')

    def validate_username(self, value):
        # Laravel alpha_dash equivalent: alphanumeric characters, dashes, and underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise serializers.ValidationError(
                "The username may only contain letters, numbers, dashes, and underscores."
            )
        
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
            
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return value.lower()

    def validate_password(self, value):
        # 1. Complexity constraints checklist
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Password must contain at least one capital letter.")
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError("Password must contain at least one small letter.")
        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError("Password must contain at least one number.")
        if not re.search(r'[@$!%*#?&.]', value):
            raise serializers.ValidationError(
                "Password must contain at least one special character (@, $, !, %, *, #, ?, &, .)."
            )

        # 2. Run core Django dictionary validation rules safely inside DRF framework boundaries
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))

        return value

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        user = authenticate(username=username, password=password)
        
        if not user:
            raise serializers.ValidationError({"detail": "Invalid credentials provided."}, code='authorization')
            
        if not user.is_active:
            raise serializers.ValidationError({"detail": "Account disabled."}, code='authorization')

<<<<<<< HEAD
        # Caching/Token logic triggered here
        token = TokenManager.create_session(user.id)

=======
>>>>>>> 55e1008 (updated password validation to prevent brute force and dictionary attack.)
        attrs['user'] = user
        attrs['token'] = token
        return attrs