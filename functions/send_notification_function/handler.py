"""SendNotificationFunction -- Lambda activada por evento (via notification-bridge).

Sin dependencias externas a proposito (solo libreria estandar): `event` que
recibe esta funcion viene directo del bridge, que ya valido el esquema
contra el contrato `ItineraryCreatedEvent v1` (ver
`services/notification-bridge/app/schema.py` y `docs/asyncapi.yaml`), asi
que aqui no se vuelve a validar -- se confia en el contrato y se falla
"ruidosamente" (excepcion) si algo esencial falta, para que el bridge lo
detecte como `FunctionError` y reintente/dead-letter segun corresponda.

Persistencia
------------
Se usa `sqlite3` (libreria estandar) para guardar un historial de
notificaciones "enviadas" (simuladas), en un archivo en `NOTIFICATION_DB_PATH`.

IMPORTANTE: `/tmp` dentro de un entorno de ejecucion Lambda es efimero por
diseno (el proveedor puede reciclar el sandbox de ejecucion en cualquier
momento, y las escrituras no sobreviven mas alla de la vida del contenedor
subyacente) y ademas es la UNICA ruta escribible: el ejecutor Lambda real de
LocalStack (Docker-outside-of-Docker, ver `docker-compose.yml`, servicio
`localstack`) corre cada invocacion en un contenedor aislado tipo AWS Lambda
real, que rechaza escrituras fuera de `/tmp` (`PermissionError`). En una
nube real, el reemplazo natural para persistencia real seria DynamoDB o RDS
(almacenamiento gestionado, fuera del ciclo de vida de la funcion); para
este proyecto academico se deja `NOTIFICATION_DB_PATH` sin configurar
(usa `DEFAULT_DB_PATH` = `/tmp/notifications.db`), asi que la deduplicacion
por `event_id` se puede observar entre invocaciones mientras el contenedor
de ejecucion siga "caliente" (reutilizado por LocalStack), pero no
sobrevive a que LocalStack recicle ese contenedor ni a un
`docker compose restart`.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone

DEFAULT_DB_PATH = "/tmp/notifications.db"


def _db_path() -> str:
    return os.environ.get("NOTIFICATION_DB_PATH", DEFAULT_DB_PATH)


def _get_connection() -> sqlite3.Connection:
    db_path = _db_path()
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_history (
            event_id TEXT PRIMARY KEY,
            itinerary_id TEXT NOT NULL,
            user_name TEXT NOT NULL,
            origin_iata TEXT NOT NULL,
            destination_iata TEXT NOT NULL,
            travel_date TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            notified_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def _already_processed(connection: sqlite3.Connection, event_id: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM notification_history WHERE event_id = ?", (event_id,)
    ).fetchone()
    return row is not None


def _record_notification(connection: sqlite3.Connection, event: dict, notified_at: str) -> None:
    data = event["data"]
    connection.execute(
        """
        INSERT INTO notification_history (
            event_id, itinerary_id, user_name, origin_iata, destination_iata,
            travel_date, duration_minutes, notified_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event["event_id"],
            data["itinerary_id"],
            data["user_name"],
            data["origin_airport"]["iata_code"],
            data["destination_airport"]["iata_code"],
            data["travel_date"],
            data["duration_minutes"],
            notified_at,
        ),
    )
    connection.commit()


def lambda_handler(event: dict, context) -> dict:
    """`event` es directamente el JSON de `ItineraryCreatedEvent v1` (el
    bridge lo pasa tal cual como Payload, sin envoltorios adicionales)."""
    event_id = event["event_id"]
    data = event["data"]
    itinerary_id = data["itinerary_id"]

    connection = _get_connection()
    try:
        if _already_processed(connection, event_id):
            # Semantica at-least-once del OutboxRelay (ADR 0002): el mismo
            # event_id puede llegar mas de una vez. Se ignora sin reprocesar.
            print(
                json.dumps(
                    {
                        "message": "duplicado, ignorado",
                        "event_id": event_id,
                        "itinerary_id": itinerary_id,
                    }
                )
            )
            return {"status": "duplicate", "event_id": event_id, "itinerary_id": itinerary_id}

        notified_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # "Envio" simulado: en un escenario real aqui iria una integracion
        # con un proveedor de email/SMS/push. Para el alcance academico del
        # proyecto, el envio se simula con un log estructurado.
        print(
            json.dumps(
                {
                    "message": "notificacion enviada (simulada)",
                    "event_id": event_id,
                    "itinerary_id": itinerary_id,
                    "notify_user": data["user_name"],
                    "trip_summary": {
                        "origin": data["origin_airport"]["iata_code"],
                        "destination": data["destination_airport"]["iata_code"],
                        "travel_date": data["travel_date"],
                        "duration_minutes": data["duration_minutes"],
                    },
                    "notified_at": notified_at,
                }
            )
        )

        _record_notification(connection, event, notified_at)
        return {"status": "sent", "event_id": event_id, "itinerary_id": itinerary_id}
    finally:
        connection.close()
