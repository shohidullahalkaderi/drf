import uuid
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.cache import cache

from .serializers import RegisterSerializer, UserSerializer

from chat.models import Message
from chat.serializers import MessageSerializer


class AuthenticationUnitTest(TestCase):

    def test_register_serializer_validation_rules(self):
        """Test validation constraints inside RegisterSerializer."""
        # 1. Assert invalid input fails constraints
        invalid_payload = {
            'username': 'sh!@#invalid',
            'email': 'invalid-email-pattern',
            'password': 'short',
            'password_confirmation': 'mismatch',
        }
        invalid_serializer = RegisterSerializer(data=invalid_payload)
        self.assertFalse(invalid_serializer.is_valid())

        # 2. Assert valid input passes constraints
        valid_payload = {
            'username': 'shohid_dev',
            'email': 'shohid@backend.io',
            'password': 'StrictSecurePasswordPattern159!',
            'password_confirmation': 'StrictSecurePasswordPattern159!',
            'first_name': 'Shohidullah',
            'last_name': 'Developer',
        }
        valid_serializer = RegisterSerializer(data=valid_payload)
        self.assertTrue(valid_serializer.is_valid())

    def test_user_serializer_data_transformation(self):
        """Test UserSerializer structural data transformations."""
        user = User.objects.create(
            username='shohid_dev',
            email='shohid@backend.io',
            first_name='Shohidullah',
            last_name='Developer'
        )

        serializer = UserSerializer(instance=user)
        data = serializer.data

        self.assertEqual(data['username'], 'shohid_dev')
        self.assertEqual(data['email'], 'shohid@backend.io')
        self.assertEqual(data['first_name'], 'Shohidullah')
        self.assertEqual(data['last_name'], 'Developer')

    def test_redis_infrastructure_connection(self):
        """Verify that Django can successfully write, read, and delete from the cache."""
        test_key = f"infra_check_{uuid.uuid4()}"
        test_value = "django_redis_operational"

        # 1. Set key-value mapping into cache storage
        cache.set(test_key, test_value, timeout=30)

        # 2. Retrieve value and assert structural match
        retrieved_value = cache.get(test_key)
        self.assertEqual(retrieved_value, test_value)

        # 3. Evict key and assert cleanup phase passed
        cache.delete(test_key)
        self.assertIsNone(cache.get(test_key))

    def test_message_serializer_and_model_constraints(self):
        """Test validation constraints and structural serialization for the Message model."""
        # 1. Assert missing or invalid fields fail serializer validation
        invalid_payload = {
            'sender_id': '',
            'message': '',
        }
        invalid_serializer = MessageSerializer(data=invalid_payload)
        self.assertFalse(invalid_serializer.is_valid())
        self.assertIn('sender_id', invalid_serializer.errors)
        self.assertIn('auth_id', invalid_serializer.errors)
        self.assertIn('message', invalid_serializer.errors)

        # 2. Assert valid payload successfully passes serializer validation and database persistence
        valid_payload = {
            'sender_id': 101,
            'auth_id': 101,
            'message': 'Hello from the automated test suite!',
        }
        valid_serializer = MessageSerializer(data=valid_payload)
        self.assertTrue(valid_serializer.is_valid())

        # Save instance to database
        message_instance = valid_serializer.save()
        self.assertIsNotNone(message_instance.id)

        # 3. Test serializer representation output
        serializer = MessageSerializer(instance=message_instance)
        data = serializer.data

        self.assertEqual(data['sender_id'], 101)
        self.assertEqual(data['auth_id'], 101)
        self.assertEqual(data['message'], 'Hello from the automated test suite!')
        self.assertIn('id', data)
        self.assertIn('created_at', data)