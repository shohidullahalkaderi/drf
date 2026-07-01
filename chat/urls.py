from django.urls import path
from .views import GroupListCreate, MessageList, RegisterView, LoginView, LogoutView, debug_user

urlpatterns = [
    path('debug-user/', debug_user, name='debug-user'),
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('groups/', GroupListCreate.as_view(), name='group-list'),
    path('groups/<str:group_name>/messages/', MessageList.as_view(), name='message-list'),
]