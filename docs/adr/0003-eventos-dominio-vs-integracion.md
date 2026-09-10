# ADR 0003 — Diferencia entre eventos de dominio y eventos de integración

## Contexto

El enunciado pide documentar explícitamente la diferencia entre ambos tipos
de evento, ya que es un punto central del diseño orientado a eventos.

## Decisión / Definiciones usadas en este proyecto

**Evento de dominio** (`ItineraryCreated`):
- Vive **dentro** del Itinerary Context, en el mismo proceso y la misma
  transacción que el caso de uso que lo generó (`CreateItineraryUseCase`).
- Su forma es rica y puede cambiar libremente porque solo lo consumen otros
  componentes del mismo bounded context (por ejemplo, para disparar la
  escritura en el outbox).
- No cruza la frontera del servicio ni tiene un contrato versionado formal.

**Evento de integración** (`ItineraryCreatedEvent v1`):
- Es la **traducción explícita** del evento de dominio a un mensaje que sí
  cruza la frontera del servicio, publicado en RabbitMQ y consumido por otro
  bounded context (Notification).
- Tiene un **contrato estable y versionado** (`itinerary.created.v1`,
  documentado en `docs/asyncapi.yaml`), con solo los campos que un consumidor
  externo necesita (ids, nombres, fecha, duración) — nunca expone detalles
  internos de la tabla `itineraries` que no forman parte del contrato.
- Cambios incompatibles requieren una nueva versión de rutina de mensajes
  (`itinerary.created.v2`), nunca rompen a los consumidores existentes.

## Consecuencias

- El Itinerary Context puede refactorizar su modelo interno sin romper a
  Notification, mientras no cambie el contrato del evento de integración.
- Queda claro en el código dónde termina la lógica de dominio (evento de
  dominio, capa `domain/`) y dónde empieza la traducción a infraestructura
  de mensajería (evento de integración, capa `infrastructure/`), reforzando
  la separación hexagonal.
