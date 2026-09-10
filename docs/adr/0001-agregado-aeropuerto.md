# ADR 0001 — Aeropuerto como referencia de valor, no como agregado replicado

## Contexto

El Itinerary Service necesita aeropuertos de salida y llegada para cada
itinerario. El aeropuerto "pertenece" conceptualmente al Airport Context
(su fuente de verdad es la API Colombia, adaptada). La pregunta de diseño es
si Itinerary Context debe mantener su propia copia completa de la entidad
Aeropuerto (agregado local, con su tabla y su ciclo de vida) o tratarla como
una referencia externa que solo se valida en el momento de uso.

## Decisión

Aeropuerto se trata en el Itinerary Context como **referencia de valor**
(similar a un "external reference" / "value object" en términos de DDD), no
como agregado completo:

- Itinerary Service **no** tiene tabla `airports` ni sincroniza un catálogo.
- Al crear un itinerario, valida `origin_airport_id` y
  `destination_airport_id` llamando directamente al Airport Service (gRPC,
  con fallback HTTP documentado) — opción "Nivel 1" explícita del enunciado.
- Guarda únicamente un **snapshot mínimo e inmutable** (id, código IATA,
  nombre, ciudad) en las columnas del itinerario, tomado en el momento de la
  validación. Ese snapshot es solo para mostrar el itinerario sin tener que
  volver a llamar al Airport Service en cada lectura; no se sincroniza si el
  aeropuerto cambia después.

## Consecuencias

- Un único dueño de la verdad para los datos de aeropuertos (Airport
  Context), sin duplicación de lógica de validación ni de sincronización.
- Un itinerario ya creado sigue siendo legible aunque Airport Service esté
  caído (usa el snapshot), pero **crear** un itinerario nuevo sí requiere que
  Airport Service esté disponible (o que su caché en Redis tenga el dato).
- Si en el futuro el negocio necesitara historial de cambios de aeropuertos
  por itinerario, o consistencia fuerte entre ambos, habría que reconsiderar
  esta decisión y evaluar una copia local optimizada (Nivel 2/3 mencionado en
  el enunciado como alternativa).
