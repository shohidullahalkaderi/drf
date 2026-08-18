import os
import sys
import django

# project root (where manage.py lives, two levels up from app/authentication/)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '../../'))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

django.setup()

from django.contrib.auth import get_user_model

# Import models and serializers from the chat app
from chat.models import Message
from chat.serializers import MessageSerializer

User = get_user_model()

# 1. Seed User Profiles
profiles = [
    {
        'username': 'backend_admin',
        'email': 'admin@enterprise.internal',
        'password': 'DevSecureAdminPass2026!',
        'first_name': 'Django',
        'last_name': 'Admin',
    }
]

for profile in profiles:
    data = profile.copy()
    username = data.pop('username')
    raw_password = data.pop('password')

    user, _ = User.objects.update_or_create(
        username=username,
        defaults=data,
    )

    user.set_password(raw_password)
    user.save()

# 2. Optional: Example of utilizing chat models/serializers during seeding if needed
# (e.g., seeding an initial chat message tied to the admin user)
# 2. Seed Initial Messages
admin_user = User.objects.filter(username='backend_admin').first()

if admin_user:
    messages = [
        {
            'sender_id': admin_user.id,
            'auth_id': admin_user.id,
            'message': 'System initialized successfully via seed script.',
        }
    ]

    for message_data in messages:
        # Always create a new database record on every seed execution
        Message.objects.create(
            sender_id=message_data['sender_id'],
            auth_id=message_data['auth_id'],
            message=message_data['message']
        )

print("Database seeding completed successfully!")