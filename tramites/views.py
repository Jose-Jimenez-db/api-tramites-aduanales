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


# Qué hace: Se arma la respuesta de una lista dividida en páginas de 5, igual que en clase.
# Qué usa: Paginator, el serializador que se le pase y Response.
# Cómo lo hace: Se divide el queryset en páginas de 5, se toma la página de ?page= y se devuelve
#     con pagina_actual, total_paginas, total_registros y resultados.
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

# Qué hace: GET y POST /api/tipos-permiso/ . Se lista el catálogo de permisos o se crea un tipo
#     nuevo.
# Qué usa: validar_rol, TipoPermiso y TipoPermisoSerializer.
# Cómo lo hace: GET lo pueden hacer todos los roles; crear es solo del Administrador. Se listan
#     ordenados por código o se valida y se guarda el nuevo (201 o 400).
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


# Qué hace: GET, PUT, PATCH y DELETE /api/tipos-permiso/<id>/ . Se ve, se edita o se borra un tipo
#     de permiso.
# Qué usa: validar_rol, TipoPermiso, TipoPermisoSerializer y ProtectedError.
# Cómo lo hace: Ver lo pueden todos; editar y borrar solo el Administrador. Se busca por id (404 si
#     no existe). Si el tipo ya se usó en trámites, el PROTECT impide borrarlo y se responde 409.
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

# Qué hace: Se arma la consulta base de trámites que usan las vistas, ya optimizada.
# Qué usa: select_related y prefetch_related del ORM.
# Cómo lo hace: select_related trae con un JOIN lo que es UNO por trámite: la carga con su cliente,
#     el transportista y el usuario que lo creó. prefetch_related trae lo que son MUCHOS por
#     trámite (los permisos con su tipo y los cobros) en consultas aparte y Django los reparte. Así
#     la lista hace siempre las mismas consultas, haya 5 o 500 trámites.
def consultar_tramites():
    return Tramite.objects.select_related(
        'carga__cliente', 'transportista', 'creado_por'
    ).prefetch_related(
        'permisos_tramite__tipo_permiso', 'cobros'
    )


# Qué hace: GET y POST /api/tramites/ . Se listan los trámites con filtros o se crea uno nuevo.
# Qué usa: validar_rol, consultar_tramites, Q, TramiteSerializer, servicios.tramite_activo_de_carga
#     y respuesta_paginada.
# Cómo lo hace: Se revisa el rol. En GET se pueden combinar ?estado=, ?tipo=, ?cliente= (filtro por
#     relación: trámite -> carga -> cliente), ?transportista= y ?buscar=, y se devuelve paginado.
#     En POST primero se validan los datos (400 si están mal), después se revisa RN-07: si la carga
#     ya tiene un trámite activo se responde 409. Si todo está bien se guarda con el usuario que lo
#     creó y se responde 201.
@api_view(['GET', 'POST'])
def tramites_api(request):
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


# Qué hace: GET, PUT, PATCH y DELETE /api/tramites/<id>/ . Se ve, se edita o se borra un trámite.
# Qué usa: validar_rol, consultar_tramites, TramiteSerializer, servicios y ProtectedError.
# Cómo lo hace: Se busca el trámite (404 si no existe). RN-12: si está LIBERADO o CANCELADO no se
#     puede editar (409). Al editar también se revisa RN-07 por si se cambia la carga. Al borrar,
#     solo se pueden borrar trámites REGISTRADOS (los demás se cancelan, 409); si tiene cobros, el
#     PROTECT lo impide y también se responde 409.
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


# Qué hace: POST /api/tramites/<id>/cambiar-estado/ con {"estado": "EN_REVISION"}. Se cambia el
#     estado del trámite.
# Qué usa: validar_rol con ESCRITURA, CambiarEstadoSerializer y las funciones de servicios.py.
# Cómo lo hace: Solo Administrador y Operador. Se busca el trámite (404), se valida que el estado
#     exista (400) y se llama a validar_cambio_estado para revisar RN-09, RN-10 y RN-11. Si hay un
#     problema se responde con su código y el motivo. Si no, se llama a cambiar_estado y se
#     devuelve el trámite actualizado.
@api_view(['POST'])
def tramite_cambiar_estado_api(request, id):
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


# Qué hace: POST /api/tramites/<id>/resolver-permiso/ con {"permiso": 3, "estado": "APROBADO",
#     "numero_resolucion": "..."}. Se aprueba o se rechaza un permiso del trámite.
# Qué usa: validar_rol con ESCRITURA, ResolverPermisoSerializer, PermisoTramite y timezone.
# Cómo lo hace: Solo Administrador y Operador. Se validan los datos (RN-15: aprobar pide número de
#     resolución). Los permisos solo se resuelven con el trámite EN_REVISION (si no, 400). Se busca
#     el permiso dentro de ese trámite (404 si no es de él) y se guarda el estado, el número y la
#     fecha de resolución.
@api_view(['POST'])
def tramite_resolver_permiso_api(request, id):
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
