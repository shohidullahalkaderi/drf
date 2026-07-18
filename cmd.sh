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

# Verify engine health via Compose services using safe single-quoted credentials
docker compose exec redis redis-cli -a 'secure_password' PING
docker compose exec db mysqladmin -u django_user -p'django_password' ping

# Grant privileges to the Django user
docker compose exec -T db mysql -u root -proot_password -e "GRANT ALL PRIVILEGES ON \`test_%\`.* TO 'django_user'@'%'; FLUSH PRIVILEGES;"

# Seed the database with initial data
docker compose exec app python manage.py seed_db
docker compose exec app python manage.py test app.authentication