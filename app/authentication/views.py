from django.db import transaction, IntegrityError
from django.core.cache import cache
from django.contrib.auth.models import User
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

class CachedTokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'token':
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


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            with transaction.atomic():
                user = serializer.save()
                
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
        token = serializer.validated_data['token']
        
        return Response({
            "user": UserSerializer(user).data,
            "token": token
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    # Bind the view to use the authentication class defined right above it
    authentication_classes = [CachedTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        TokenManager.destroy_session(request.auth)
        TokenManager.clear_cached_user(request.user.id)
        return Response({"detail": "Successfully logged out from active session."}, status=status.HTTP_200_OK)