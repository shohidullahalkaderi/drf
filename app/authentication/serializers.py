import secrets
from django.core.cache import cache
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

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


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'first_name', 'last_name')

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return value.lower()

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

        # Caching/Token logic triggered here
        token = TokenManager.create_session(user.id)

        attrs['user'] = user
        attrs['token'] = token
        return attrs