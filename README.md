# Sistema de Itinerarios Personales

Sistema de planificación de viajes que integra tres estilos arquitectónicos:
**microservicios**, **arquitectura basada en eventos** y **serverless
(FaaS)**, construido para el reto académico "Sistema de itinerarios
personales" (Nivel 1 + Nivel 2 + Nivel 3).

> Estado del documento: en construcción incremental. Las secciones marcadas
> `[pendiente]` se completan en la etapa final de consolidación (diagramas
> renderizados, evidencia de ejecución y tabla de autoevaluación), una vez
> validado el sistema completo con `docker compose up`.

## 1. Arquitectura utilizada

| Estilo | Dónde se aplica | Cómo se demuestra |
|---|---|---|
| Microservicios | Airport Service, Itinerary Service | Servicios independientes, cada uno con su propia base de datos/estado, comunicados por HTTP/gRPC |
| Basada en eventos | Itinerary Service → RabbitMQ → Notification | Transactional Outbox + evento de integración versionado (`docs/asyncapi.yaml`) |
| Serverless (FaaS) | Notification Service, Reportes | Funciones Lambda en LocalStack, activadas por evento o bajo demanda, sin servidor permanente |

Infraestructura compartida: API Gateway (FastAPI), RabbitMQ, Redis, Postgres
(uno por servicio con datos relacionales), LocalStack, Vault, Toxiproxy,
OpenTelemetry + Jaeger, Prometheus + Grafana.

## 2. Contextos Delimitados (Bounded Contexts) y Lenguaje Ubicuo (DDD)

### 2.1 Airport Context (Contexto de Aeropuertos)

Responsable de conocer los aeropuertos colombianos y exponerlos en un
formato de dominio propio, desacoplado de la API externa.

| Término (ubicuo) | Significado |
|---|---|
| Aeropuerto (`Airport`) | Entidad con id, nombre, código IATA, ciudad, latitud/longitud |
| Puerto de Repositorio (`AirportRepositoryPort`) | Contrato del dominio para obtener aeropuertos, sin saber cómo se implementa |
| Adaptador API Colombia (`ApiColombiaAdapter`) | Implementación del puerto que traduce la respuesta externa al modelo de dominio |
| Adaptador con Caché (`CachingAirportAdapter`) | Decorador del adaptador anterior que aplica cache-aside sobre Redis |
| Disyuntor (`CircuitBreaker`) | Mecanismo que corta las llamadas a la API externa cuando falla repetidamente |

### 2.2 Itinerary Context (Contexto de Itinerarios)

Responsable del ciclo de vida de los itinerarios de viaje del usuario.

| Término (ubicuo) | Significado |
|---|---|
| Itinerario (`Itinerary`) | Agregado raíz: nombre del usuario, aeropuerto de salida/llegada (referencia de valor, ver ADR 0001), fecha, duración |
| Caso de Uso (`CreateItineraryUseCase`, etc.) | Orquesta validación + persistencia + evento de dominio |
| Evento de Dominio (`ItineraryCreated`) | Ver ADR 0003 |
| Buzón de Salida (`OutboxEvent`) | Fila transaccional que garantiza la publicación futura del evento de integración (ADR 0002) |
| Evento de Integración (`ItineraryCreatedEvent v1`) | Ver ADR 0003 y `docs/asyncapi.yaml` |

### 2.3 Notification Context (Contexto de Notificaciones)

Responsable de reaccionar a la creación de itinerarios y de generar reportes
bajo demanda, sin mantener un servidor encendido permanentemente.

| Término (ubicuo) | Significado |
|---|---|
| Función de Notificación (`SendNotificationFunction`) | Lambda activada al recibir `ItineraryCreatedEvent` |
| Función de Reporte (`GenerateItineraryReportFunction`) | Lambda invocada bajo demanda para consolidar métricas |
| Puente de Mensajería (`notification-bridge`) | Traduce mensajes de RabbitMQ a invocaciones Lambda (ver sección 5) |

Los tres contextos se comunican **solo** a través de contratos explícitos
(HTTP/gRPC para Airport↔Itinerary, eventos de integración para
Itinerary→Notification) — ningún contexto accede directamente a la base de
datos de otro.

## 3. Patrón Adapter (implementación real)

```
domain/ports.py            -> interfaz AirportRepositoryPort (el "Puerto")
infrastructure/api_colombia_adapter.py -> ApiColombiaAdapter (el "Adapter")
infrastructure/caching_adapter.py      -> CachingAirportAdapter (decora al Adapter)
```

- El dominio de Airport Service (casos de uso) depende únicamente de
  `AirportRepositoryPort`, nunca de detalles de la API externa.
- `ApiColombiaAdapter` traduce el JSON crudo de `api-colombia.com` a la
  entidad `Airport` del dominio (nombres de campo, tipos, ausencia de datos).
- El frontend y los demás servicios **solo** conocen el modelo adaptado
  (expuesto por REST `/api/v1/airports` y por gRPC `airport.v1.AirportService`).
- Esto permite reemplazar la API Colombia por cualquier otra fuente sin tocar
  el dominio ni los consumidores.

## 4. Arquitectura Hexagonal

Cada microservicio (Airport, Itinerary) se organiza en las mismas capas:

```
app/
├── domain/          # Entidades, value objects, puertos (interfaces). Sin dependencias externas.
├── application/     # Casos de uso que orquestan el dominio a través de los puertos.
├── infrastructure/  # Adapters concretos: HTTP externo, Postgres, Redis, RabbitMQ, gRPC.
└── api/             # Routers FastAPI, esquemas Pydantic, inyección de dependencias.
```

La regla de dependencia es siempre hacia adentro: `api` e `infrastructure`
dependen de `domain`, nunca al revés.

## 5. Flujo asíncrono de notificaciones

1. `POST /api/v1/itineraries` en Itinerary Service valida los aeropuertos
   (gRPC a Airport Service) y guarda el itinerario + una fila en
   `outbox_events`, en una sola transacción (ADR 0002).
2. `OutboxRelay` publica `ItineraryCreatedEvent v1` en el exchange
   `itinerary.events` de RabbitMQ.
3. `notification-bridge` consume la cola, y por cada mensaje invoca (AWS SDK
   `lambda:Invoke`) la función `SendNotificationFunction` en LocalStack. Este
   puente existe porque RabbitMQ no es un origen de eventos nativo de AWS
   Lambda; es la pieza mínima necesaria para que el broker "active" la
   función, cumpliendo el espíritu serverless (la función no corre hasta que
   hay un evento, y no mantiene estado entre invocaciones).
4. `SendNotificationFunction` simula el envío (log estructurado) y guarda el
   historial en su propio almacenamiento, deduplicando por `event_id`.
5. `GenerateItineraryReportFunction` se invoca bajo demanda (no reacciona a
   eventos) para consolidar métricas sin sobrecargar los servicios
   principales.

## 6. Double Write Problem

Ver ADR 0002 (`docs/adr/0002-double-write-problem.md`).

## 7. Decisión sobre el Agregado Aeropuerto

Ver ADR 0001 (`docs/adr/0001-agregado-aeropuerto.md`).

## 8. Eventos de dominio vs. eventos de integración

Ver ADR 0003 (`docs/adr/0003-eventos-dominio-vs-integracion.md`).

## 9. Diagramas

`[pendiente]` — se agregan en la etapa de consolidación: componentes, clases,
relacional, secuencia (frontend → gateway → itinerary → airport), despliegue.

## 10. Instrucciones para ejecutar el proyecto

`[pendiente de validar con Docker instalado]`. Resumen previsto:

```bash
cp .env.example .env
docker compose up --build
# Frontend:        http://localhost:8080
# API Gateway:     http://localhost:8000/docs
# Airport Service: http://localhost:8001/docs
# Itinerary Svc:   http://localhost:8002/docs
# RabbitMQ mgmt:   http://localhost:15672 (guest/guest)
# Jaeger UI:       http://localhost:16686
# Prometheus:      http://localhost:9090
# Grafana:         http://localhost:3000 (admin/admin)
```

## 11. Tabla de autoevaluación

`[pendiente]` — se completa al final, con honestidad sobre qué quedó
verificado end-to-end (requiere Docker, no disponible en la máquina usada
para generar el código) y qué quedó como código/config entregado sin
ejecución en vivo (Kubernetes, CI/CD real, Chaos Engineering).
