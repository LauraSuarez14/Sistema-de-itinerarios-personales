# notification-bridge
#
# El build context es la RAIZ del repositorio (ver docker-compose.yml:
# `context: .`, `dockerfile: services/notification-bridge/Dockerfile`), por
# eso las rutas COPY de abajo empiezan en `libs/common/` y
# `services/notification-bridge/` en vez de rutas relativas a este archivo
# (mismo patron que `services/itinerary-service/Dockerfile`).
FROM python:3.11-slim AS base

WORKDIR /app

# --- Dependencias Python -------------------------------------------------
COPY services/notification-bridge/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Paquete compartido `itinerarios-common` (libs/common), instalado aparte
# porque no es un paquete publicado en PyPI sino codigo del propio monorepo.
COPY libs/common /tmp/libs/common
RUN pip install --no-cache-dir /tmp/libs/common && rm -rf /tmp/libs/common

# --- Codigo de la app ------------------------------------------------------
COPY services/notification-bridge/app ./app

ENV PYTHONUNBUFFERED=1

EXPOSE 8090

CMD ["python", "-m", "app.main"]
