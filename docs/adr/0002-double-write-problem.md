# ADR 0002 — Resolución del Double Write Problem con Transactional Outbox

## Contexto

Al crear un itinerario, Itinerary Service debe (a) persistirlo en PostgreSQL
y (b) publicar `ItineraryCreatedEvent` en RabbitMQ para que Notification
funcione de forma desacoplada. Si estas dos escrituras se hacen por separado
(guardar en BD y luego publicar en el broker como dos pasos independientes),
existe una ventana de inconsistencia — el **Double Write Problem**: si el
proceso falla entre el `commit` de la BD y la publicación en el broker, el
itinerario queda guardado pero el evento nunca se publica (o viceversa, si se
publica antes de confirmar la escritura en BD, se puede notificar algo que
luego falla al guardar).

## Decisión

Se aplica el patrón **Transactional Outbox**:

1. En la misma transacción de base de datos que inserta el itinerario, se
   inserta también una fila en la tabla `outbox_events` (mismo commit
   atómico: o se guardan ambas filas, o ninguna).
2. Un proceso `OutboxRelay`, en background dentro del propio Itinerary
   Service, hace polling periódico (`OUTBOX_RELAY_INTERVAL_SECONDS`) de filas
   `outbox_events` con `published_at IS NULL`, las publica en RabbitMQ
   (exchange `itinerary.events`) usando *publisher confirms*, y solo entonces
   marca la fila como publicada.
3. Si el proceso muere entre el commit y la publicación, al reiniciar el
   relay simplemente retoma las filas pendientes — no se pierde el evento.
4. El consumidor (SendNotificationFunction) es **idempotente**: guarda el
   `event_id` procesado y descarta duplicados, porque el relay puede, en
   casos raros de caída justo después de publicar y antes de marcar
   `published_at`, reenviar un evento ya publicado (semántica *at-least-once*
   deliberada, nunca *at-most-once*).

## Consecuencias

- Se garantiza que todo itinerario creado eventualmente tiene su evento
  publicado (at-least-once), a costa de una pequeña latencia de polling.
- Se traslada la responsabilidad de deduplicación al consumidor, lo cual es
  el patrón estándar y evita bloqueos distribuidos (2PC) entre PostgreSQL y
  RabbitMQ.
- En un entorno productivo real esto se reemplazaría por CDC (Debezium leyendo
  el WAL de PostgreSQL) para evitar el polling; se documenta como
  simplificación consciente para el alcance del proyecto.
