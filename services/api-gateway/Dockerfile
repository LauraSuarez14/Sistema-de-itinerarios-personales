# Build context = raíz del repo (ver docker-compose.yml: context: .)
FROM python:3.11-slim

WORKDIR /app

COPY services/api-gateway/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Paquete compartido de utilidades transversales (logging, otel, correlation,
# jwt). El gateway es el emisor del JWT, por eso depende de common.security.
COPY libs/common /libs/common
RUN pip install --no-cache-dir /libs/common

COPY services/api-gateway/app ./app

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "app.main"]
