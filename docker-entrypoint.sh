#!/bin/sh
set -e

echo "==> Ejecutando migraciones..."
python manage.py migrate --no-input

echo "==> Iniciando gunicorn en puerto ${PORT:-8000}..."
exec gunicorn ApiRiego.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile -

