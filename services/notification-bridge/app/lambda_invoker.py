"""Adapter boto3 que invoca la funcion Lambda `SendNotificationFunction` en
LocalStack. Es la unica pieza del bridge que conoce AWS SDK / boto3; el
resto del codigo (`processor.py`) solo conoce el puerto implicito
`invoke(payload) -> dict` (duck typing, igual que los tests con un fake)."""
from __future__ import annotations

import json
import logging

import boto3

from .errors import LambdaInvocationError

logger = logging.getLogger(__name__)


class LambdaInvoker:
    def __init__(
        self,
        function_name: str,
        endpoint_url: str,
        region_name: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
    ) -> None:
        self._function_name = function_name
        self._client = boto3.client(
            "lambda",
            endpoint_url=endpoint_url,
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

    def invoke(self, payload: dict) -> dict:
        """Invoca la funcion en modo sincrono (`RequestResponse`) para poder
        loguear el resultado real de la invocacion (no solo "se encolo")."""
        response = self._client.invoke(
            FunctionName=self._function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode("utf-8"),
        )
        status_code = response.get("StatusCode")
        function_error = response.get("FunctionError")
        raw_body = response["Payload"].read()

        if status_code != 200 or function_error:
            raise LambdaInvocationError(
                f"Invocation of {self._function_name} failed "
                f"(status_code={status_code}, function_error={function_error}, "
                f"body={raw_body!r})"
            )

        if not raw_body:
            return {}
        try:
            return json.loads(raw_body)
        except json.JSONDecodeError:
            logger.warning("Lambda %s returned a non-JSON body: %r", self._function_name, raw_body)
            return {}
