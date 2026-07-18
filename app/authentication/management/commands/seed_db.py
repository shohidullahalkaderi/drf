from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError

class Command(BaseCommand):
    help = 'Seeds initial backend developer and test system profiles safely.'

    def handle(self, *args, **options):
        self.stdout.write('Initializing database migration data seed...')

        users_to_seed = [
            {
                "username": "backend_admin",
                "email": "admin@enterprise.internal",
                "password": "DevSecureAdminPass2026!",
                "is_superuser": True
            },
            {
                "username": "qa_tester",
                "email": "tester@enterprise.internal",
                "password": "TestAutomationPass2026!",
                "is_superuser": False
            }
        ]

        try:
            # Wrap in an atomic block so the entire seed fails or succeeds together
            with transaction.atomic():
                for user_data in users_to_seed:
                    username = user_data['username']
                    email = user_data['email']
                    password = user_data['password']
                    is_superuser = user_data['is_superuser']

                    # Check for both duplicate username AND duplicate email to match registration logic
                    if User.objects.filter(username=username).exists() or User.objects.filter(email__iexact=email).exists():
                        self.stdout.write(self.style.WARNING(
                            f"Profile configuration or email for '{username}' already registered. Skipping."
                        ))
                        continue

                    # Explicitly use the correct creation method based on permission level
                    if is_superuser:
                        User.objects.create_superuser(
                            username=username,
                            email=email,
                            password=password
                        )
                    else:
                        User.objects.create_user(
                            username=username,
                            email=email,
                            password=password
                        )
                    
                    self.stdout.write(self.style.SUCCESS(f"Successfully seeded target profile: {username}"))
                    
            self.stdout.write(self.style.SUCCESS('Database population seeding protocol completed.'))

        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f"Critical Database error occurred during seeding transaction: {e}"))