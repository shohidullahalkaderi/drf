from django.db import transaction, IntegrityError
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token 

from .serializers import (
    RegisterSerializer, 
    LoginSerializer, 
    UserSerializer
)

User = get_user_model()

# Custom class defined inside the file
class BearerTokenAuthentication(TokenAuthentication):
    keyword = 'Bearer'


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            with transaction.atomic():
                user = serializer.save()
                token, _ = Token.objects.get_or_create(user=user)
                
            return Response({
                "user": UserSerializer(user).data,
                "token": token.key
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
        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    # 2. Tell this view specifically to look for the "Bearer" token prefix
    authentication_classes = [BearerTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response({"detail": "Successfully logged out from active session."}, status=status.HTTP_200_OK)