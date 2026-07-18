from django.contrib.auth.models import User
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .serializers import TokenManager


class AuthenticationFlowTests(APITestCase):

    def setUp(self):
        # Clear the cache before every test execution to prevent data bleeding
        cache.clear()
        
        # Setup helper endpoints (Change names if your urls.py uses different routing names)
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')

        # Dummy payload parameters
        self.valid_user_data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "SecurePassword123!",
            "first_name": "John",
            "last_name": "Doe"
        }

    def tearDown(self):
        # Ensure clean state post-execution
        cache.clear()

    def test_successful_registration(self):
        """Ensure a user can register and receive a valid session token."""
        response = self.client.post(self.register_url, self.valid_user_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], self.valid_user_data['username'])
        
        # Verify that the session token was successfully written into the cache architecture
        token = response.data['token']
        user_id = TokenManager.get_user_id(token)
        self.assertIsNotNone(user_id)
        self.assertEqual(user_id, response.data['user']['id'])

    def test_registration_duplicate_email(self):
        """Registration must enforce case-insensitive unique constraints on email addresses."""
        # Create initial target user
        User.objects.create_user(username="existing", email="testuser@example.com", password="password123")
        
        # Attempt to register with identical email but unique username
        payload = self.valid_user_data.copy()
        payload['username'] = "different_username"
        
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_successful_login(self):
        """Valid credentials must authorize a user and generate a working cache mapping."""
        # Pre-seed user record
        user = User.objects.create_user(
            username=self.valid_user_data['username'],
            email=self.valid_user_data['email'],
            password=self.valid_user_data['password']
        )

        login_payload = {
            "username": self.valid_user_data['username'],
            "password": self.valid_user_data['password']
        }
        
        response = self.client.post(self.login_url, login_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        
        # Verify token mapping points directly back to the correct user primary key
        token = response.data['token']
        self.assertEqual(TokenManager.get_user_id(token), user.id)

    def test_login_invalid_credentials(self):
        """Invalid credentials must safely reject authorization."""
        User.objects.create_user(username="testuser", password="RightPassword")

        login_payload = {
            "username": "testuser",
            "password": "WrongPassword"
        }
        
        response = self.client.post(self.login_url, login_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_login_deactivated_user(self):
        """Inactive accounts should not be allowed validation authorization access."""
        user = User.objects.create_user(username="disableduser", password="password123")
        user.is_active = False
        user.save()

        login_payload = {"username": "disableduser", "password": "password123"}
        response = self.client.post(self.login_url, login_payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_authenticated_request_and_caching(self):
        """Valid token must grant access and trigger user database model caching."""
        user = User.objects.create_user(username="authuser", password="password123")
        token = TokenManager.create_session(user.id)

        # Append custom authorization token prefix matching the header spec
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        
        # Hit logout or any generic view requiring IsAuthenticated to verify identity authorization pipeline
        response = self.client.post(self.logout_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Post-logout token session must be purged from memory store cache completely
        self.assertIsNone(TokenManager.get_user_id(token))
        self.assertIsNone(cache.get(f"user_profile_{user.id}"))

    def test_request_with_expired_or_invalid_token(self):
        """Invalid headers must return an explicit 401 unauthenticated flag layout."""
        self.client.credentials(HTTP_AUTHORIZATION='Token fake_expired_or_invalid_token_hex')
        
        response = self.client.post(self.logout_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)