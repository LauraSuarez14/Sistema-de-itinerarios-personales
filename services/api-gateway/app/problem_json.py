"""Helper para construir respuestas de error consistentes en formato RFC 7807
(application/problem+json), replicando el mismo formato que usan Airport
Service e Itinerary Service, para que el cliente (frontend) trate los errores
de forma homogénea sin importar qué servicio los originó."""
from __future__ import annotations

from fastapi.responses import JSONResponse


def problem_response(status_code: int, title: str, detail: str, instance: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": title,
            "status": status_code,
            "detail": detail,
            "instance": instance,
        },
    )
