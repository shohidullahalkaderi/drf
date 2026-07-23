import re
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

User = get_user_model()


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
    first_name = serializers.CharField(
        max_length=50, 
        required=False, 
        allow_blank=True, 
        default=''
    )
    last_name = serializers.CharField(
        max_length=50, 
        required=False, 
        allow_blank=True, 
        default=''
    )

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

        # 2. Core Django password validators
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
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True, 
        write_only=True, 
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        # Normalize email input to lowercase to align with RegisterSerializer
        email = attrs.get('email', '').strip().lower()
        password = attrs.get('password')

        # Retrieve username corresponding to the provided email address
        try:
            user_obj = User.objects.get(email__iexact=email)
            username = user_obj.get_username()
        except User.DoesNotExist:
            username = None

        # Authenticate against Django's authentication system
        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=password
        )

        if not user:
            raise serializers.ValidationError(
                {"detail": "Invalid credentials provided."}, 
                code='authorization'
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "Account disabled."}, 
                code='authorization'
            )

        attrs['user'] = user
        return attrs