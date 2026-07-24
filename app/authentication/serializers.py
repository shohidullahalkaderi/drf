import re
import uuid
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, status
from rest_framework.exceptions import APIException, PermissionDenied

User = get_user_model()


class CustomBadRequest(APIException):
    """Custom exception to force a flat dictionary response with HTTP 400."""
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail):
        self.detail = detail


class CustomUnauthorized(APIException):
    """Custom exception to force a flat dictionary response with HTTP 401."""
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self, detail):
        self.detail = detail


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'}
    )
    password_confirmation = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'}
    )

    username = serializers.CharField(
        min_length=3, 
        max_length=50, 
        required=False, 
        allow_blank=True, 
        allow_null=True,
        default=''
    )
    first_name = serializers.CharField(
        max_length=50, 
        required=False, 
        allow_blank=True, 
        allow_null=True,
        default=''
    )
    last_name = serializers.CharField(
        max_length=50, 
        required=False, 
        allow_blank=True, 
        allow_null=True,
        default=''
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirmation', 'first_name', 'last_name')

    def validate(self, attrs):
        db_error = {"detail": "Invalid registration credentials provided."}
        
        email = (attrs.get('email') or '').strip().lower()
        password = attrs.get('password') or ''
        password_confirmation = attrs.get('password_confirmation') or ''
        username = (attrs.get('username') or '').strip()

        # 1. Compare password with password_confirmation
        if not password or not password_confirmation or password != password_confirmation:
            raise CustomBadRequest(db_error)

        # 2. Validate Email Presence & Uniqueness
        if not email or User.objects.filter(email__iexact=email).exists():
            raise CustomBadRequest(db_error)
        attrs['email'] = email

        # 3. Validate Username (if provided)
        if username:
            if not re.match(r'^[a-zA-Z0-9_-]+$', username) or User.objects.filter(username__iexact=username).exists():
                raise CustomBadRequest(db_error)

        # 4. Validate Password Complexity
        if len(password) < 8 or \
           not re.search(r'[A-Z]', password) or \
           not re.search(r'[a-z]', password) or \
           not re.search(r'[0-9]', password) or \
           not re.search(r'[@$!%*#?&.]', password):
            raise CustomBadRequest(db_error)

        try:
            validate_password(password)
        except DjangoValidationError:
            raise CustomBadRequest(db_error)

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirmation', None)
        
        email = validated_data['email']
        username = (validated_data.get('username') or '').strip()

        if not username:
            base_name = re.sub(r'[^a-zA-Z0-9_-]', '', email.split('@')[0])[:30] or 'user'
            username = f"{base_name}_{uuid.uuid4().hex[:8]}"

        return User.objects.create_user(
            username=username,
            email=email,
            password=validated_data['password'],
            first_name=validated_data.get('first_name') or '',
            last_name=validated_data.get('last_name') or ''
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=False, 
        allow_blank=True, 
        allow_null=True,
        default=''
    )
    password = serializers.CharField(
        required=False, 
        write_only=True, 
        allow_blank=True,
        allow_null=True,
        default='',
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        from django.contrib.auth import authenticate

        email = (attrs.get('email') or '').strip().lower()
        password = attrs.get('password') or ''

        # 1. Missing, null, or blank email/password -> HTTP 400 Bad Request
        if not email or not password:
            raise CustomBadRequest({"detail": "Invalid login credentials provided."})

        try:
            user_obj = User.objects.get(email__iexact=email)
            username = user_obj.get_username()
        except User.DoesNotExist:
            username = None

        user = authenticate(
            request=self.context.get('request'), 
            username=username, 
            password=password
        )

        # 2. Wrong email or password -> HTTP 401 Unauthorized
        if not user:
            raise CustomUnauthorized({"detail": "Invalid login credentials provided."})

        # 3. Disabled account -> HTTP 403 Forbidden
        if not user.is_active:
            raise PermissionDenied({"detail": "Account disabled."})

        attrs['user'] = user
        return attrs