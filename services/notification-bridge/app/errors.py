"""Excepciones compartidas. Separadas de `lambda_invoker.py` (que importa
`boto3`) para que `processor.py` y los tests puedan importarlas sin arrastrar
boto3 como dependencia obligatoria de los tests unitarios."""
from __future__ import annotations


class LambdaInvocationError(Exception):
    """La invocacion a la Lambda no tuvo status 200 o devolvio FunctionError."""
