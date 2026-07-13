docker builder prune -f
docker compose down --remove-orphans
docker compose down -v
docker compose build --no-cache
docker compose up -d
docker compose exec app python manage.py migrate
docker exec django_redis redis-cli -a secure_password PING
docker exec django_mysql_db mysqladmin -u django_user -pdjango_password ping