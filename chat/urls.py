# chat/urls.py

from django.urls import path
from .views import SendMessageView, ChatStreamView

urlpatterns = [
    path('chat/send/', SendMessageView.as_view(), name='chat-send'),
    path('chat/stream/', ChatStreamView.as_view(), name='chat-stream'),
]