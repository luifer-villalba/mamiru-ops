#!/bin/sh
set -e

run_migrations_with_retries() {
    max_attempts="${MIGRATE_MAX_ATTEMPTS:-10}"
    attempt=1

    while [ "$attempt" -le "$max_attempts" ]; do
        echo "Ejecutando migraciones (intento ${attempt}/${max_attempts})..."
        if python manage.py migrate; then
            return 0
        fi

        if [ "$attempt" -eq "$max_attempts" ]; then
            echo "Error: no se pudieron aplicar migraciones tras ${max_attempts} intentos."
            return 1
        fi

        echo "Base de datos no disponible aun. Reintentando en 3 segundos..."
        attempt=$((attempt + 1))
        sleep 3
    done
}

if [ "${RUN_SETUP:-true}" = "true" ]; then
    run_migrations_with_retries

    if [ "${RUN_COLLECTSTATIC:-true}" = "true" ]; then
        echo "Recolectando archivos estaticos..."
        python manage.py collectstatic --noinput
    else
        echo "RUN_COLLECTSTATIC=false, omitiendo collectstatic."
    fi
fi

echo "Iniciando Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
