#!/bin/sh
# Entrypoint del contenedor: espera a que Postgres acepte conexiones, corre
# las migraciones de Alembic (idempotente: `upgrade head` no hace nada si ya
# esta al dia) y luego arranca la app. Esto evita condiciones de carrera con
# el healthcheck de `itinerary-db` en docker-compose, que solo garantiza que
# el proceso de Postgres esta arriba, no que la red interna ya este lista en
# el instante exacto en que este contenedor arranca.
set -e

: "${ITINERARY_DB_HOST:=itinerary-db}"
: "${ITINERARY_DB_PORT:=5432}"

echo "[entrypoint] Waiting for database at ${ITINERARY_DB_HOST}:${ITINERARY_DB_PORT}..."

attempt=0
max_attempts=30
until python -c "
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect(('${ITINERARY_DB_HOST}', ${ITINERARY_DB_PORT}))
except OSError:
    sys.exit(1)
finally:
    s.close()
"; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge "$max_attempts" ]; then
        echo "[entrypoint] Database not reachable after ${max_attempts} attempts, giving up."
        exit 1
    fi
    echo "[entrypoint] Database not ready yet (attempt ${attempt}/${max_attempts}), retrying in 2s..."
    sleep 2
done

echo "[entrypoint] Database reachable. Running Alembic migrations..."
alembic upgrade head

echo "[entrypoint] Starting Itinerary Service..."
exec python -m app.main
