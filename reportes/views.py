"""
Reportes de solo lectura (GET). Los tres roles pueden consultarlos.
Las consultas ORM están en reportes/consultas.py.
"""
from datetime import date

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from cuentas.permisos import TODOS, validar_rol

from . import consultas


@api_view(['GET'])
def resumen_clientes_api(request):
    """GET /api/reportes/resumen-clientes/   ?solo_con_saldo=true"""
    error = validar_rol(request, TODOS)
    if error:
        return error

    datos = consultas.resumen_por_cliente()
    if request.query_params.get('solo_con_saldo', '').lower() == 'true':
        datos = datos.filter(saldo_pendiente__gt=0)
    return Response(list(datos))


@api_view(['GET'])
def tramites_por_estado_api(request):
    """GET /api/reportes/tramites-por-estado/"""
    error = validar_rol(request, TODOS)
    if error:
        return error
    return Response(consultas.tramites_por_estado())


@api_view(['GET'])
def listos_para_liberar_api(request):
    """GET /api/reportes/listos-para-liberar/"""
    error = validar_rol(request, TODOS)
    if error:
        return error

    datos = []
    for t in consultas.tramites_listos_para_liberar():
        datos.append({
            'id': t.id,
            'codigo': t.codigo,
            'contenedor': t.carga.numero_contenedor,
            'cliente': t.carga.cliente.nombre,
            'transportista': t.transportista.nombre,
            'placa_cabezal': t.transportista.placa_cabezal,
        })
    return Response({'cantidad': len(datos), 'tramites': datos})


@api_view(['GET'])
def licencias_por_vencer_api(request):
    """GET /api/reportes/licencias-por-vencer/   ?dias=30 (de 1 a 365)"""
    error = validar_rol(request, TODOS)
    if error:
        return error

    dias = request.query_params.get('dias', '30')
    if not dias.isdigit() or not 1 <= int(dias) <= 365:
        return Response({'dias': 'Debe ser un número entre 1 y 365.'}, status=status.HTTP_400_BAD_REQUEST)
    dias = int(dias)

    datos = []
    for t in consultas.licencias_por_vencer(dias):
        datos.append({
            'id': t.id,
            'nombre': t.nombre,
            'placa_cabezal': t.placa_cabezal,
            'vencimiento_licencia': t.vencimiento_licencia,
            'tramites_activos': t.tramites_activos,
        })
    return Response({'dias': dias, 'transportistas': datos})


@api_view(['GET'])
def ingresos_api(request):
    """GET /api/reportes/ingresos/   ?desde=AAAA-MM-DD (inicio del mes)  ?hasta=AAAA-MM-DD (hoy)"""
    error = validar_rol(request, TODOS)
    if error:
        return error

    try:
        hasta = date.fromisoformat(request.query_params.get('hasta', str(timezone.localdate())))
        desde = date.fromisoformat(request.query_params.get('desde', str(hasta.replace(day=1))))
    except ValueError:
        return Response({'error': 'Use fechas con el formato AAAA-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

    if desde > hasta:
        return Response(
            {'desde': 'La fecha inicial no puede ser mayor que la final.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    resultado = consultas.ingresos_por_concepto(desde, hasta)
    return Response({'desde': desde, 'hasta': hasta, **resultado})


@api_view(['GET'])
def permisos_pendientes_api(request):
    """GET /api/reportes/permisos-pendientes/"""
    error = validar_rol(request, TODOS)
    if error:
        return error

    datos = []
    for fila in consultas.permisos_pendientes_por_institucion():
        datos.append({
            'institucion': fila['tipo_permiso__institucion'],
            'permisos_pendientes': fila['cantidad'],
            'tramites_afectados': fila['tramites'],
        })
    return Response(datos)
