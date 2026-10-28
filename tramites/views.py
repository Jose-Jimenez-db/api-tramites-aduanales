from django.core.paginator import Paginator
from django.db.models import ProtectedError, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from cuentas.permisos import ESCRITURA, SOLO_ADMIN, TODOS, validar_rol

from . import servicios
from .models import PermisoTramite, TipoPermiso, Tramite
from .serializers import (
    CambiarEstadoSerializer,
    PermisoTramiteSerializer,
    ResolverPermisoSerializer,
    TipoPermisoSerializer,
    TramiteSerializer,
)


def respuesta_paginada(queryset, serializer_class, page_number):
    paginator = Paginator(queryset, 5)
    page = paginator.get_page(page_number)
    serializer = serializer_class(page.object_list, many=True)
    return Response({
        'pagina_actual': page.number,
        'total_paginas': paginator.num_pages,
        'total_registros': paginator.count,
        'resultados': serializer.data
    })


# ---------------------------------------------------------------------------
# Catálogo de tipos de permiso (solo el Administrador lo modifica)
# ---------------------------------------------------------------------------

@api_view(['GET', 'POST'])
def tipos_permiso_api(request):
    error = validar_rol(request, TODOS if request.method == 'GET' else SOLO_ADMIN)
    if error:
        return error

    if request.method == 'GET':
        tipos = TipoPermiso.objects.order_by('codigo')
        return Response(TipoPermisoSerializer(tipos, many=True).data)

    serializer = TipoPermisoSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def tipo_permiso_detalle_api(request, id):
    error = validar_rol(request, TODOS if request.method == 'GET' else SOLO_ADMIN)
    if error:
        return error

    try:
        tipo = TipoPermiso.objects.get(id=id)
    except TipoPermiso.DoesNotExist:
        return Response({'error': 'Tipo de permiso no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(TipoPermisoSerializer(tipo).data)

    if request.method in ['PUT', 'PATCH']:
        serializer = TipoPermisoSerializer(tipo, data=request.data, partial=request.method == 'PATCH')
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        tipo.delete()
    except ProtectedError:
        return Response(
            {'error': 'El tipo de permiso ya se usó en trámites. Desactívelo en lugar de borrarlo.'},
            status=status.HTTP_409_CONFLICT
        )
    return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Trámites
# ---------------------------------------------------------------------------

def consultar_tramites():
    """
    select_related: carga, cliente y transportista en la misma consulta (JOIN).
    prefetch_related: permisos (con su tipo) y cobros en consultas aparte.
    """
    return Tramite.objects.select_related(
        'carga__cliente', 'transportista', 'creado_por'
    ).prefetch_related(
        'permisos_tramite__tipo_permiso', 'cobros'
    )


@api_view(['GET', 'POST'])
def tramites_api(request):
    """
    Filtros combinables:
    ?estado=APROBADO  ?tipo=IMPORTACION  ?cliente=1  ?transportista=2  ?buscar=texto  ?page=2
    """
    error = validar_rol(request)
    if error:
        return error

    if request.method == 'GET':
        tramites = consultar_tramites().order_by('-fecha_creacion', '-id')
        estado = request.query_params.get('estado')
        tipo = request.query_params.get('tipo')
        cliente = request.query_params.get('cliente')
        transportista = request.query_params.get('transportista')
        buscar = request.query_params.get('buscar')

        if estado:
            tramites = tramites.filter(estado=estado.upper())
        if tipo:
            tramites = tramites.filter(tipo=tipo.upper())
        if cliente:
            if not cliente.isdigit():
                return Response({'cliente': 'Debe ser un número.'}, status=status.HTTP_400_BAD_REQUEST)
            # Filtro por relación: trámite -> carga -> cliente
            tramites = tramites.filter(carga__cliente_id=cliente)
        if transportista:
            if not transportista.isdigit():
                return Response({'transportista': 'Debe ser un número.'}, status=status.HTTP_400_BAD_REQUEST)
            tramites = tramites.filter(transportista_id=transportista)
        if buscar:
            tramites = tramites.filter(
                Q(codigo__icontains=buscar) |
                Q(carga__numero_contenedor__icontains=buscar) |
                Q(carga__cliente__nombre__icontains=buscar)
            )

        return respuesta_paginada(
            tramites, TramiteSerializer,
            request.query_params.get('page', 1)
        )

    serializer = TramiteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # RN-07: una carga solo puede tener un trámite activo
    carga = serializer.validated_data['carga']
    otro = servicios.tramite_activo_de_carga(carga)
    if otro:
        return Response(
            {'error': f'La carga {carga} ya tiene un trámite activo ({otro.codigo}).'},
            status=status.HTTP_409_CONFLICT
        )

    tramite = serializer.save(creado_por=request.user)
    return Response(
        TramiteSerializer(consultar_tramites().get(id=tramite.id)).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def tramite_detalle_api(request, id):
    error = validar_rol(request)
    if error:
        return error

    try:
        tramite = consultar_tramites().get(id=id)
    except Tramite.DoesNotExist:
        return Response({'error': 'Trámite no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(TramiteSerializer(tramite).data)

    if request.method in ['PUT', 'PATCH']:
        # RN-12: un trámite liberado o cancelado no se modifica
        if tramite.estado in Tramite.ESTADOS_CERRADOS:
            return Response(
                {'error': 'El trámite está liberado o cancelado y no se puede modificar.'},
                status=status.HTTP_409_CONFLICT
            )

        serializer = TramiteSerializer(tramite, data=request.data, partial=request.method == 'PATCH')
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # RN-07 también al cambiar la carga
        carga = serializer.validated_data.get('carga')
        if carga and servicios.tramite_activo_de_carga(carga, excluir_id=tramite.id):
            return Response(
                {'error': f'La carga {carga} ya tiene un trámite activo.'},
                status=status.HTTP_409_CONFLICT
            )

        serializer.save()
        return Response(TramiteSerializer(consultar_tramites().get(id=id)).data)

    # RN-12: solo se eliminan trámites recién registrados; los demás se cancelan
    if tramite.estado != Tramite.Estado.REGISTRADO:
        return Response(
            {'error': 'Solo se pueden eliminar trámites en estado REGISTRADO. Use la cancelación.'},
            status=status.HTTP_409_CONFLICT
        )
    try:
        tramite.delete()
    except ProtectedError:
        return Response(
            {'error': 'El trámite tiene cobros registrados. Cancélelo en lugar de borrarlo.'},
            status=status.HTTP_409_CONFLICT
        )
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def tramite_cambiar_estado_api(request, id):
    """POST /api/tramites/{id}/cambiar-estado/   {"estado": "EN_REVISION"}"""
    error = validar_rol(request, ESCRITURA)
    if error:
        return error

    try:
        tramite = Tramite.objects.select_related('transportista').get(id=id)
    except Tramite.DoesNotExist:
        return Response({'error': 'Trámite no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = CambiarEstadoSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    nuevo_estado = serializer.validated_data['estado']

    # Reglas RN-09, RN-10 y RN-11
    problema = servicios.validar_cambio_estado(tramite, nuevo_estado)
    if problema:
        codigo_http, mensaje = problema
        return Response({'error': mensaje}, status=codigo_http)

    servicios.cambiar_estado(tramite, nuevo_estado)
    return Response(TramiteSerializer(consultar_tramites().get(id=id)).data)


@api_view(['POST'])
def tramite_resolver_permiso_api(request, id):
    """POST /api/tramites/{id}/resolver-permiso/   {"permiso": 3, "estado": "APROBADO", "numero_resolucion": "..."}"""
    error = validar_rol(request, ESCRITURA)
    if error:
        return error

    try:
        tramite = Tramite.objects.get(id=id)
    except Tramite.DoesNotExist:
        return Response({'error': 'Trámite no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ResolverPermisoSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    datos = serializer.validated_data

    # RN-15: los permisos solo se resuelven con el trámite EN_REVISION
    if tramite.estado != Tramite.Estado.EN_REVISION:
        return Response(
            {'error': 'Los permisos solo se pueden resolver cuando el trámite está EN_REVISION.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        permiso = tramite.permisos_tramite.select_related('tipo_permiso').get(id=datos['permiso'])
    except PermisoTramite.DoesNotExist:
        return Response(
            {'error': 'El permiso indicado no pertenece a este trámite.'},
            status=status.HTTP_404_NOT_FOUND
        )

    permiso.estado = datos['estado']
    permiso.numero_resolucion = datos['numero_resolucion'].strip()
    permiso.fecha_resolucion = timezone.now()
    permiso.save()
    return Response(PermisoTramiteSerializer(permiso).data)
