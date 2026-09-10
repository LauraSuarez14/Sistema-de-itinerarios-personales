"""Carga de secretos dinámicos desde HashiCorp Vault (modo dev) al arrancar
cada servicio. Si Vault no está disponible (por ejemplo en una ejecución
local simple sin el perfil completo de docker-compose), se degrada de forma
controlada a las variables de entorno para no bloquear el arranque."""
from __future__ import annotations

import os

import hvac

from .logging import get_logger

logger = get_logger(__name__)


def load_secrets(mount_path: str, env_fallback_keys: list[str]) -> dict[str, str]:
    """Lee `secret/data/<mount_path>` de Vault (KV v2). Devuelve un dict con
    las claves encontradas; para cualquier clave de `env_fallback_keys` que no
    esté en Vault, se completa con la variable de entorno homónima."""
    result: dict[str, str] = {}

    vault_addr = os.getenv("VAULT_ADDR")
    vault_token = os.getenv("VAULT_TOKEN")

    if vault_addr and vault_token:
        try:
            client = hvac.Client(url=vault_addr, token=vault_token)
            if client.is_authenticated():
                response = client.secrets.kv.v2.read_secret_version(
                    path=mount_path, raise_on_deleted_version=True
                )
                result = dict(response["data"]["data"])
                logger.info("secrets loaded from vault", extra={"mount_path": mount_path})
        except Exception as exc:  # noqa: BLE001 - degradar sin tumbar el servicio
            logger.warning(
                "vault unreachable, falling back to environment variables",
                extra={"error": str(exc)},
            )

    for key in env_fallback_keys:
        result.setdefault(key, os.getenv(key, ""))

    return result
