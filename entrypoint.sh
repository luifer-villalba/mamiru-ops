#!/bin/sh
set -e

if [ "${RUN_SETUP:-true}" = "true" ]; then
    echo "Ejecutando migraciones..."
    python manage.py migrate

    echo "Recolectando archivos estaticos..."
    python manage.py collectstatic --noinput
fi

echo "Iniciando Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
