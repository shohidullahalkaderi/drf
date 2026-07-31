# Clean up build cache and reset stack environment
docker builder prune -f
docker compose down --remove-orphans
docker compose down -v

# Rebuild microservice layers from scratch and boot
docker compose build --no-cache
docker compose up -d

# Execute framework migrations and verify directory state
docker compose exec app python manage.py migrate
docker compose exec app ls -la /usr/src/app

# Seed the database and run test
docker compose exec app python manage.py seed
docker compose exec app python manage.py test --settings=app.settings_test