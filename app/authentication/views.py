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
    UserSerializer,
    CustomThrottled
)
from .throttles import (
    LoginRateThrottle, 
    RegisterRateThrottle, 
    LogoutRateThrottle
)

User = get_user_model()


class BearerTokenAuthentication(TokenAuthentication):
    keyword = 'Bearer'

    def authenticate_credentials(self, key):
        try:
            return super().authenticate_credentials(key)
        except exceptions.AuthenticationFailed:
            raise exceptions.AuthenticationFailed({"detail": "Invalid auth token provided."})


class BaseThrottledView(APIView):
    """Base API view that intercepts DRF throttling exceptions inline."""
    def throttled(self, request, wait):
        raise CustomThrottled({"detail": f"Too many requests. Please try again in {int(wait)} seconds."})


class RegisterView(BaseThrottledView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegisterRateThrottle]

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


class LoginView(BaseThrottledView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
            
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key
        }, status=status.HTTP_200_OK)


class LogoutView(BaseThrottledView):
    authentication_classes = [BearerTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [LogoutRateThrottle]

    def initial(self, request, *args, **kwargs):
        # 1. Run throttle check BEFORE DRF tries to authenticate the token
        self.check_throttles(request)
        
        # 2. Proceed to standard DRF authentication and permissions
        super().initial(request, *args, **kwargs)

    def post(self, request):
        request.auth.delete()
        return Response(
            {"detail": "Successfully logged out."}, 
            status=status.HTTP_200_OK
        )