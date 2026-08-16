# chat/serializers.py

from rest_framework import serializers
from .models import Message

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'sender_id', 'auth_id', 'message', 'created_at']
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {
            'sender_id': {'required': True, 'allow_null': False},
            'auth_id': {'required': True, 'allow_null': False},
            'message': {'required': True, 'allow_blank': False},
        }