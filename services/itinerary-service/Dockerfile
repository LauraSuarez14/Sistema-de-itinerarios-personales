# Itinerary Service
#
# El build context es la RAIZ del repositorio (ver docker-compose.yml:
# `context: .`, `dockerfile: services/itinerary-service/Dockerfile`), por
# eso las rutas COPY de abajo empiezan en `proto/`, `libs/common/` y
# `services/itinerary-service/` en vez de rutas relativas a este archivo.
FROM python:3.11-slim AS base

# Dependencias minimas de build: aunque psycopg2-binary y grpcio ya traen
# wheels precompilados para la plataforma habitual (linux/amd64), se instala
# gcc por si toca compilar en una plataforma sin wheel disponible (p.ej.
# arm64 en Apple Silicon sin --platform explicito).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Dependencias Python -----------------------------------------------
COPY services/itinerary-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Paquete compartido `itinerarios-common` (libs/common), instalado aparte
# porque no es un paquete publicado en PyPI sino codigo del propio monorepo.
COPY libs/common /tmp/libs/common
RUN pip install --no-cache-dir /tmp/libs/common && rm -rf /tmp/libs/common

# --- Codigo de la app y contrato gRPC ------------------------------------
COPY proto/airport.proto /tmp/proto/airport.proto
COPY services/itinerary-service/app ./app
COPY services/itinerary-service/alembic ./alembic
COPY services/itinerary-service/alembic.ini ./alembic.ini
COPY services/itinerary-service/docker-entrypoint.sh ./docker-entrypoint.sh

# Genera los stubs gRPC del contrato `airport.proto` DENTRO de la imagen
# (nunca se commitean al repo, ver .gitignore). `app/infrastructure/grpc_client/`
# ya existe como paquete (tiene `__init__.py`) porque se copio junto con
# `app/` en el paso anterior.
RUN python -m grpc_tools.protoc \
        -I/tmp/proto \
        --python_out=app/infrastructure/grpc_client \
        --grpc_python_out=app/infrastructure/grpc_client \
        /tmp/proto/airport.proto \
    # El codigo generado por protoc usa `import airport_pb2` (import
    # absoluto), que solo funciona si ese modulo esta en sys.path a nivel
    # raiz. Como aqui vive dentro del paquete `app.infrastructure.grpc_client`,
    # se reescribe a un import relativo explicito para que funcione como
    # parte del paquete de la aplicacion.
    && sed -i 's/^import airport_pb2/from . import airport_pb2/' \
        app/infrastructure/grpc_client/airport_pb2_grpc.py \
    && rm -rf /tmp/proto

RUN chmod +x ./docker-entrypoint.sh

ENV PYTHONUNBUFFERED=1 \
    ITINERARY_HTTP_PORT=8002

EXPOSE 8002

ENTRYPOINT ["./docker-entrypoint.sh"]
