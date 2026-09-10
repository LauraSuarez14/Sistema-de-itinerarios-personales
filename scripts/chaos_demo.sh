#!/usr/bin/env bash
# Demostración de resiliencia (Nivel 2) y Chaos Engineering (Nivel 3):
# inyecta latencia/caídas controladas contra el stub local de API Colombia
# (infra/toxiproxy/mock-api-colombia) usando la API de administración de
# Toxiproxy, y muestra al Airport Service reaccionar con reintentos y,
# finalmente, con el circuit breaker abriéndose.
#
# Requiere: docker compose up (con TOXIPROXY_ENABLED=true en .env) y curl.
set -euo pipefail

TOXIPROXY_ADMIN="http://localhost:8474"
AIRPORT_URL="http://localhost:8001"

echo "== 1. Estado inicial del proxy =="
curl -s "$TOXIPROXY_ADMIN/proxies/api_colombia" | tee /dev/stderr
echo

echo "== 2. Llamada normal (debería responder rápido y en 200) =="
time curl -s -o /dev/null -w "status=%{http_code} time=%{time_total}s\n" "$AIRPORT_URL/api/v1/airports/1"

echo
echo "== 3. Inyectando latencia de 6s (mayor al timeout del cliente) =="
curl -s -X POST "$TOXIPROXY_ADMIN/proxies/api_colombia/toxics" \
  -H "Content-Type: application/json" \
  -d '{"name":"latencia_alta","type":"latency","attributes":{"latency":6000,"jitter":500}}'
echo

echo "== 4. Repitiendo llamadas para forzar reintentos y abrir el circuit breaker =="
for i in $(seq 1 6); do
  time curl -s -o /dev/null -w "intento $i -> status=%{http_code} time=%{time_total}s\n" "$AIRPORT_URL/api/v1/airports/1" || true
done

echo
echo "== 5. Verificando métrica de estado del circuit breaker (1 = abierto) =="
curl -s "$AIRPORT_URL/metrics" | grep airport_circuit_breaker_state || true

echo
echo "== 6. Restaurando la red (quitando el toxic) =="
curl -s -X DELETE "$TOXIPROXY_ADMIN/proxies/api_colombia/toxics/latencia_alta"
echo
echo "Listo. Espera ~30s (recovery_timeout del breaker) y vuelve a llamar a $AIRPORT_URL/api/v1/airports/1 para ver que vuelve a CLOSED."
