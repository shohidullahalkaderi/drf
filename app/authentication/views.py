from django.db import transaction, IntegrityError
<<<<<<< HEAD
from django.core.cache import cache
from django.contrib.auth.models import User
=======
from django.contrib.auth import get_user_model
>>>>>>> 55e1008 (updated password validation to prevent brute force and dictionary attack.)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, authentication, exceptions

from .serializers import (
    RegisterSerializer, 
    LoginSerializer, 
    UserSerializer, 
    TokenManager, 
    USER_CACHE_EXPIRY_SECONDS
)

<<<<<<< HEAD
class CachedTokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        parts = auth_header.split()
        # CHANGED: Check for 'bearer' instead of 'token'
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None

        token = parts[1]
        user_id = TokenManager.get_user_id(token)
        
        if not user_id:
            raise exceptions.AuthenticationFailed('Invalid or expired authentication token.')

        # In-Memory Cache Lookup for the User Profile object
        cache_key = f"user_profile_{user_id}"
        user = cache.get(cache_key)

        if not user:
            try:
                user = User.objects.get(pk=user_id)
                cache.set(cache_key, user, USER_CACHE_EXPIRY_SECONDS)
            except User.DoesNotExist:
                raise exceptions.AuthenticationFailed('User account no longer exists.')

        if not user.is_active:
            raise exceptions.AuthenticationFailed('User account is currently deactivated.')

        return (user, token)

    def authenticate_header(self, request):
        return 'Token'
=======
User = get_user_model()

# 1. Custom class defined inside the file
class BearerTokenAuthentication(TokenAuthentication):
    keyword = 'Bearer'
>>>>>>> 55e1008 (updated password validation to prevent brute force and dictionary attack.)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            with transaction.atomic():
                user = serializer.save()
<<<<<<< HEAD
=======
                token, _ = Token.objects.get_or_create(user=user)
>>>>>>> 55e1008 (updated password validation to prevent brute force and dictionary attack.)
                
            token = TokenManager.create_session(user.id)
            return Response({
                "user": UserSerializer(user).data,
                "token": token
            }, status=status.HTTP_201_CREATED)
            
        except IntegrityError:
            return Response(
                {"detail": "Database error during registration. Username or Email might have just been taken."}, 
                status=status.HTTP_409_CONFLICT
            )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        user = serializer.validated_data['user']
<<<<<<< HEAD
        token = serializer.validated_data['token']
=======
        token, _ = Token.objects.get_or_create(user=user)
>>>>>>> 55e1008 (updated password validation to prevent brute force and dictionary attack.)
        
        return Response({
            "user": UserSerializer(user).data,
            "token": token
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
<<<<<<< HEAD
    # Bind the view to use the authentication class defined right above it
    authentication_classes = [CachedTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        TokenManager.destroy_session(request.auth)
        TokenManager.clear_cached_user(request.user.id)
=======
    # 2. Tell this view specifically to look for the "Bearer" token prefix
    authentication_classes = [BearerTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.auth.delete()
>>>>>>> 55e1008 (updated password validation to prevent brute force and dictionary attack.)
        return Response({"detail": "Successfully logged out from active session."}, status=status.HTTP_200_OK)