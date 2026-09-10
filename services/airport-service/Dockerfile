# Build context = raíz del repo (ver docker-compose.yml: context: .)
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/airport-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Paquete compartido de utilidades transversales (logging, otel, jwt, vault).
COPY libs/common /libs/common
RUN pip install --no-cache-dir /libs/common

# Genera los stubs gRPC del contrato compartido proto/airport.proto dentro
# del paquete app.grpc_server, y corrige el import generado por protoc para
# que funcione como import relativo de paquete.
COPY proto /tmp/proto
COPY services/airport-service/app ./app
RUN python -m grpc_tools.protoc \
      -I/tmp/proto \
      --python_out=./app/grpc_server \
      --grpc_python_out=./app/grpc_server \
      /tmp/proto/airport.proto \
    && sed -i 's/^import airport_pb2 as airport__pb2/from . import airport_pb2 as airport__pb2/' ./app/grpc_server/airport_pb2_grpc.py

EXPOSE 8001
EXPOSE 50051

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "app.main"]
