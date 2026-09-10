# Vault (modo dev)

El contenedor `vault` en `docker-compose.yml` corre en **modo dev** de
HashiCorp Vault (`hashicorp/vault:1.17`), con auto-unseal y un root token
fijo tomado de `VAULT_TOKEN` (`.env`). Esto es válido únicamente para
desarrollo/demostración académica — nunca para un Vault productivo real
(que requeriría unseal manual con shares de Shamir, TLS, políticas por
servicio, etc., fuera del alcance de este proyecto).

## Cómo se usa

1. Al levantar `docker compose up`, Vault queda escuchando en `:8200` pero
   **vacío** (sin secretos).
2. Corre `scripts/vault_seed.sh` (requiere `curl`; toma `VAULT_ADDR`/
   `VAULT_TOKEN` del entorno o usa los valores por defecto de `.env.example`)
   para sembrar los secretos que cada servicio espera en
   `secret/data/<nombre-del-servicio>`.
3. Cada servicio (`airport-service`, `itinerary-service`, `api-gateway`) usa
   `common.vault_client.load_secrets(mount_path, env_fallback_keys)` al
   arrancar: si Vault tiene el secreto, lo usa; si Vault no está disponible o
   el secreto no existe, cae de forma controlada a la variable de entorno
   homónima (para no bloquear ejecuciones locales simples sin el perfil
   completo de infraestructura).

## Verificación manual

```bash
curl -H "X-Vault-Token: dev-only-token" http://localhost:8200/v1/secret/data/airport-service
```
