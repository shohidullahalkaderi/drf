from rest_framework import generics, status
from .models import ChatGroup, Message
from .serializers import ChatGroupSerializer, MessageSerializer, UserSerializer, LoginSerializer
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from django.contrib.auth.models import User
from django.contrib.auth import logout

from django.http import JsonResponse

def debug_user(request):
    try:
        count = User.objects.count()
        return JsonResponse({'status': 'ok', 'user_count': count})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Registration
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key
        }, status=status.HTTP_201_CREATED)

# Login (custom to return token + user info)
class LoginView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "user_id": user.pk,
            "username": user.username
        })

# Logout (delete token)
class LogoutView(generics.GenericAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        request.user.auth_token.delete()
        logout(request)
        return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)

class GroupListCreate(generics.ListCreateAPIView):
    authentication_classes = [TokenAuthentication]  # optional
    permission_classes = [AllowAny]                 # no auth required
    queryset = ChatGroup.objects.all()
    serializer_class = ChatGroupSerializer

class MessageList(generics.ListAPIView):
    authentication_classes = [TokenAuthentication]  # optional
    permission_classes = [AllowAny]                 # no auth required
    serializer_class = MessageSerializer

    def get_queryset(self):
        group_name = self.kwargs['group_name']
        group = ChatGroup.objects.get(name=group_name)
        return Message.objects.filter(group=group)