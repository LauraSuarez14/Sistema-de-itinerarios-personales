# Pruebas E2E (Testcontainers)

Levanta el sistema completo con `docker-compose.yml` real (vía
`testcontainers.compose.DockerCompose`) y ejercita el flujo
frontend→gateway→itinerary→airport→RabbitMQ→notification-bridge→Lambda de
punta a punta, destruyendo todos los contenedores al finalizar.

> **No ejecutado en el entorno donde se generó este proyecto** (no hay
> Docker instalado en esa máquina — ver limitaciones en el README raíz).
> Requiere Docker Desktop/Engine corriendo localmente.

## Cómo correrlo

```bash
pip install -r tests/e2e/requirements.txt
pytest tests/e2e/test_full_flow.py -v -s
```

La primera corrida puede tardar varios minutos (build de todas las
imágenes). El timeout de espera de salud del sistema es de 180s; si tu
máquina es más lenta, ajusta `_wait_for_healthy(..., timeout=...)`.
