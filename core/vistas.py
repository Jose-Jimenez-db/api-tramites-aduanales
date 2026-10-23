from django.http import JsonResponse


def no_encontrado(request, exception=None):
    return JsonResponse(
        {
            "estado": 404,
            "codigo": "no_encontrado",
            "mensaje": "La ruta solicitada no existe.",
            "detalle": None,
        },
        status=404,
    )


def error_interno(request):
    return JsonResponse(
        {
            "estado": 500,
            "codigo": "error_interno",
            "mensaje": "Ocurrió un error interno. Intente de nuevo más tarde.",
            "detalle": None,
        },
        status=500,
    )
