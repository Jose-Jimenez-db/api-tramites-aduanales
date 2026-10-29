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


# Qué hace: GET /api/reportes/resumen-clientes/ . Se devuelve la consulta Q1 (resumen por cliente).
# Qué usa: validar_rol con TODOS y consultas.resumen_por_cliente.
# Cómo lo hace: Cualquier rol puede verlo. Si viene ?solo_con_saldo=true se dejan solo los clientes
#     que deben algo (saldo_pendiente mayor que 0).
@api_view(['GET'])
def resumen_clientes_api(request):
    error = validar_rol(request, TODOS)
    if error:
        return error

    datos = consultas.resumen_por_cliente()
    if request.query_params.get('solo_con_saldo', '').lower() == 'true':
        datos = datos.filter(saldo_pendiente__gt=0)
    return Response(list(datos))


# Qué hace: GET /api/reportes/tramites-por-estado/ . Se devuelve la consulta Q2 (trámites por
#     estado y por tipo).
# Qué usa: validar_rol con TODOS y consultas.tramites_por_estado.
# Cómo lo hace: Se revisa que el usuario tenga sesión y se devuelve el resultado tal cual.
@api_view(['GET'])
def tramites_por_estado_api(request):
    error = validar_rol(request, TODOS)
    if error:
        return error
    return Response(consultas.tramites_por_estado())


# Qué hace: GET /api/reportes/listos-para-liberar/ . Se devuelve la consulta Q3 (trámites listos
#     para liberar).
# Qué usa: validar_rol con TODOS y consultas.tramites_listos_para_liberar.
# Cómo lo hace: Se recorre el resultado y de cada trámite se arma un diccionario con el código, el
#     contenedor, el cliente, el transportista y la placa. Se devuelve la cantidad y la lista.
@api_view(['GET'])
def listos_para_liberar_api(request):
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


# Qué hace: GET /api/reportes/licencias-por-vencer/?dias=30 . Se devuelve la consulta Q4.
# Qué usa: validar_rol con TODOS, isdigit y consultas.licencias_por_vencer.
# Cómo lo hace: Si no se manda ?dias= se usa 30. Se revisa que sea un número entre 1 y 365; si no,
#     400. Después se arma la lista de transportistas con su fecha de vencimiento y sus trámites
#     activos.
@api_view(['GET'])
def licencias_por_vencer_api(request):
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


# Qué hace: GET /api/reportes/ingresos/?desde=AAAA-MM-DD&hasta=AAAA-MM-DD . Se devuelve la consulta
#     Q5.
# Qué usa: validar_rol con TODOS, date.fromisoformat, timezone y consultas.ingresos_por_concepto.
# Cómo lo hace: Si no vienen fechas, hasta es hoy y desde es el primer día del mes. Si una fecha no
#     tiene el formato AAAA-MM-DD se responde 400, y también si desde es mayor que hasta. Se
#     devuelve el rango con el detalle por concepto y el total.
@api_view(['GET'])
def ingresos_api(request):
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


# Qué hace: GET /api/reportes/permisos-pendientes/ . Se devuelve la consulta Q6.
# Qué usa: validar_rol con TODOS y consultas.permisos_pendientes_por_institucion.
# Cómo lo hace: Se recorre el resultado y se cambian los nombres de las llaves para que se
#     entiendan mejor (institucion, permisos_pendientes, tramites_afectados).
@api_view(['GET'])
def permisos_pendientes_api(request):
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
