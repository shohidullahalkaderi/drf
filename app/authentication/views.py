from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import status, permissions, exceptions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token 

from .serializers import (
    RegisterSerializer, 
    LoginSerializer, 
    UserSerializer
)

User = get_user_model()


class BearerTokenAuthentication(TokenAuthentication):
    keyword = 'Bearer'

    def authenticate_credentials(self, key):
        try:
            return super().authenticate_credentials(key)
        except exceptions.AuthenticationFailed:
            raise exceptions.AuthenticationFailed({"detail": "Invalid auth token provided."})


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
            
        with transaction.atomic():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
            
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    authentication_classes = [BearerTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response(
            {"detail": "Successfully logged out."}, 
            status=status.HTTP_200_OK
        )