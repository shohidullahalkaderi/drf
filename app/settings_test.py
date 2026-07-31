from app.settings import *
# This test checks if the database connection is using SQLite in-memory database: ('file:memorydb_default?mode=memory&cache=shared')
# docker compose exec app python manage.py test --settings=app.settings_test -v 2
# kubectl exec deployment/app -n django-stack -- python manage.py test --settings=app.settings_test -v 2
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}