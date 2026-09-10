#!/usr/bin/env bash
# Siembra los secretos dinámicos que cada servicio lee al arrancar
# (ver libs/common/common/vault_client.py::load_secrets), usando la API HTTP
# de Vault directamente (no requiere el CLI `vault` instalado en el host).
# Vault corre aquí en modo dev (ver docker-compose.yml), con el root token
# fijado por VAULT_DEV_ROOT_TOKEN_ID = VAULT_TOKEN (.env) — esto es válido
# SOLO para desarrollo local, nunca para un Vault real.
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-dev-only-token}"

put_secret() {
  local path="$1"; shift
  local json="{"
  local first=true
  for kv in "$@"; do
    key="${kv%%=*}"
    value="${kv#*=}"
    if [ "$first" = true ]; then first=false; else json+=","; fi
    json+="\"$key\":\"$value\""
  done
  json+="}"

  curl -s -X POST \
    -H "X-Vault-Token: $VAULT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"data\": $json}" \
    "$VAULT_ADDR/v1/secret/data/$path" > /dev/null
  echo "Secreto escrito en secret/data/$path"
}

put_secret "airport-service" \
  "OAUTH2_CLIENT_SECRET=${OAUTH2_CLIENT_SECRET:-dev-client-secret-change-me}" \
  "JWT_SECRET_KEY=${JWT_SECRET_KEY:-dev-secret-change-me}"

put_secret "itinerary-service" \
  "ITINERARY_DB_PASSWORD=${ITINERARY_DB_PASSWORD:-itinerary-db-pass}" \
  "OAUTH2_CLIENT_SECRET=${OAUTH2_CLIENT_SECRET:-dev-client-secret-change-me}" \
  "JWT_SECRET_KEY=${JWT_SECRET_KEY:-dev-secret-change-me}"

put_secret "api-gateway" \
  "JWT_SECRET_KEY=${JWT_SECRET_KEY:-dev-secret-change-me}"

echo "Listo. Reinicia los servicios (docker compose restart airport-service itinerary-service api-gateway) para que relean los secretos al arrancar."
