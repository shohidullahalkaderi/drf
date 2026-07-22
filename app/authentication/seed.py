import os, sys, django

# project root (where manage.py lives)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '../../'))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

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

print(f"Database seeding completed successfully!")