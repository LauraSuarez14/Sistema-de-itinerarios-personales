#!/usr/bin/env python3
"""Invoca `GenerateItineraryReportFunction` contra LocalStack y muestra el
resultado por consola. Pensado para correrse desde el HOST (no dentro de un
contenedor), por eso el default de `AWS_ENDPOINT_URL` aqui es
`http://localhost:4566` (el puerto que docker-compose publica), a diferencia
de `http://localstack:4566` que usan los servicios entre si dentro de la red
de Docker.

Uso:
    python scripts/generate_report.py

Requiere `boto3` instalado (`pip install boto3`) y que
`docker compose up localstack` ya haya corrido
`infra/localstack/init/01_create_functions.sh` (se ejecuta automaticamente
al arrancar LocalStack).
"""
from __future__ import annotations

import json
import os
import sys

import boto3


def main() -> int:
    endpoint_url = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")
    region_name = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID", "test")
    aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "test")
    function_name = os.environ.get("GENERATE_REPORT_FUNCTION_NAME", "GenerateItineraryReportFunction")

    client = boto3.client(
        "lambda",
        endpoint_url=endpoint_url,
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )

    print(f"Invocando {function_name} en {endpoint_url}...")
    response = client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=b"{}",
    )

    payload = json.loads(response["Payload"].read() or b"{}")

    if response.get("FunctionError"):
        print(f"FunctionError: {response['FunctionError']}", file=sys.stderr)
        print(json.dumps(payload, indent=2, ensure_ascii=False), file=sys.stderr)
        return 1

    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if payload.get("status") == "skipped":
        print(
            "\n[nota] La funcion no pudo autenticarse contra Itinerary Service "
            "(INTERNAL_SERVICE_TOKEN no configurado). Ver docstring de "
            "functions/generate_itinerary_report_function/handler.py.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
