#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import time
import socket


def wait_for_db() -> None:
    """Waits for the MySQL database container to accept network connections."""
    db_host = os.environ.get('DB_HOST', 'db')
    try:
        db_port = int(os.environ.get('DB_PORT', 3306))
    except ValueError:
        db_port = 3306

    # Only run the wait check if starting the server or handling migrations
    target_commands = {'runserver', 'migrate', 'makemigrations', 'inspectdb'}
    if len(sys.argv) > 1 and sys.argv[1] in target_commands:
        print(f"Checking network availability on {db_host}:{db_port}...", flush=True)
        
        while True:
            # Create a fresh socket instance on every iteration loop
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    s.connect((db_host, db_port))
                print("Database is up and accepting connections! Proceeding...", flush=True)
                break
            except (socket.timeout, socket.error):
                print("Database port is not ready yet. Retrying in 2 seconds...", flush=True)
                time.sleep(2)


def main() -> None:
    """Run administrative tasks."""
    # Django 5 structure defaults to 'app.settings' or your explicit project folder name
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
    
    # Block execution until the network socket dependency answers
    wait_for_db()

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()