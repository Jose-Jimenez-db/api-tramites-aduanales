"""
Manejo centralizado de errores.

Todas las respuestas de error de la API tienen la misma forma:

    {
        "estado": 400,
        "codigo": "datos_invalidos",
        "mensaje": "Texto para el usuario",
        "detalle": {...} o null
    }

Nunca se devuelven trazas internas (stack traces) al cliente.
"""
import logging

from django.db import IntegrityError
from django.db.models import ProtectedError, RestrictedError
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("core")

CODIGOS = {
    400: "datos_invalidos",
    401: "no_autenticado",
    403: "sin_permiso",
    404: "no_encontrado",
    405: "metodo_no_permitido",
    409: "conflicto",
    415: "tipo_no_soportado",
    429: "demasiadas_solicitudes",
}


class Conflicto(APIException):
    """Error 409: la operación choca con el estado actual de los datos."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "La operación entra en conflicto con el estado actual del recurso."
    default_code = "conflicto"


def manejador_de_errores(exc, context):
    # Errores de la base de datos que deben verse como 409 y no como 500
    if isinstance(exc, (ProtectedError, RestrictedError)):
        exc = Conflicto(
            "No se puede eliminar el registro porque tiene información relacionada."
        )
    elif isinstance(exc, IntegrityError):
        exc = Conflicto("El registro entra en conflicto con datos ya existentes.")

    respuesta = exception_handler(exc, context)

    if respuesta is None:
        # Error no previsto: se registra en el servidor y se responde sin trazas.
        logger.exception("Error no controlado en %s", context.get("view"))
        return Response(
            {
                "estado": 500,
                "codigo": "error_interno",
                "mensaje": "Ocurrió un error interno. Intente de nuevo más tarde.",
                "detalle": None,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    datos = respuesta.data
    if respuesta.status_code == 404:
        mensaje = "El recurso solicitado no existe."
        if isinstance(datos, dict) and "matches the given query" not in str(datos.get("detail", "")):
            mensaje = str(datos.get("detail", mensaje))
        detalle = None
    elif isinstance(datos, dict) and set(datos.keys()) == {"detail"}:
        mensaje = str(datos["detail"])
        detalle = None
    else:
        mensaje = "Los datos enviados no son válidos."
        detalle = datos

    respuesta.data = {
        "estado": respuesta.status_code,
        "codigo": CODIGOS.get(respuesta.status_code, "error"),
        "mensaje": mensaje,
        "detalle": detalle,
    }
    return respuesta
