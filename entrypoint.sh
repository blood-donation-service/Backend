#!/bin/sh
set -e

echo "[entrypoint] Waiting for database at ${DB_HOST:-db}:${DB_PORT:-5432}..."
until nc -z "${DB_HOST:-db}" "${DB_PORT:-5432}"; do
  sleep 1
done
echo "[entrypoint] Database is up."

echo "[entrypoint] Applying database migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Collecting static files..."
python manage.py collectstatic --noinput || true

touch /app/django.log
chown www-data:www-data /app/django.log 2>/dev/null || true
chmod 664 /app/django.log

echo "[entrypoint] Starting: $@"
exec "$@"
