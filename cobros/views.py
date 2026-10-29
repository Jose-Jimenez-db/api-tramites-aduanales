from django.core.paginator import Paginator
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from cuentas.permisos import ESCRITURA, SOLO_ADMIN, validar_rol

from .models import Cobro
from .serializers import CobroSerializer, RegistrarPagoSerializer


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


# Qué hace: RN-13: se revisa si el trámite ya tiene un cobro vigente de ese mismo concepto.
# Qué usa: El modelo Cobro, filter, exclude y exists.
# Cómo lo hace: Se buscan los cobros del trámite con ese concepto que no estén anulados. Si se
#     manda excluir_id, se deja por fuera ese cobro (sirve al editar). Se devuelve True o False.
def concepto_repetido(tramite, concepto, excluir_id=None):
    cobros = Cobro.objects.filter(tramite=tramite, concepto=concepto).exclude(estado='ANULADO')
    if excluir_id:
        cobros = cobros.exclude(id=excluir_id)
    return cobros.exists()


# Qué hace: GET y POST /api/cobros/ . Se listan los cobros con filtros y orden, o se registra un
#     cobro nuevo.
# Qué usa: validar_rol, select_related, CobroSerializer, concepto_repetido y respuesta_paginada.
# Cómo lo hace: Se revisa el rol. En GET se traen los cobros con su trámite, carga, cliente y
#     usuario en la misma consulta. Se pueden combinar ?estado=, ?concepto=, ?tramite= y ?cliente=
#     (relación de tres saltos). Para ?ordenar= se usa lstrip('-') para revisar que el campo esté
#     permitido. En POST se valida (400) y se revisa que el concepto no esté repetido (409). Si
#     todo está bien se guarda con el usuario que lo registró y se responde 201.
@api_view(['GET', 'POST'])
def cobros_api(request):
    error = validar_rol(request)
    if error:
        return error

    if request.method == 'GET':
        cobros = Cobro.objects.select_related('tramite__carga__cliente', 'registrado_por')
        estado = request.query_params.get('estado')
        concepto = request.query_params.get('concepto')
        tramite = request.query_params.get('tramite')
        cliente = request.query_params.get('cliente')
        ordenar = request.query_params.get('ordenar', '-fecha_emision')

        if estado:
            cobros = cobros.filter(estado=estado.upper())
        if concepto:
            cobros = cobros.filter(concepto=concepto.upper())
        if tramite:
            if not tramite.isdigit():
                return Response({'tramite': 'Debe ser un número.'}, status=status.HTTP_400_BAD_REQUEST)
            cobros = cobros.filter(tramite_id=tramite)
        if cliente:
            if not cliente.isdigit():
                return Response({'cliente': 'Debe ser un número.'}, status=status.HTTP_400_BAD_REQUEST)
            # Filtro por relación: cobro -> trámite -> carga -> cliente
            cobros = cobros.filter(tramite__carga__cliente_id=cliente)

        if ordenar.lstrip('-') not in ['fecha_emision', 'monto', 'fecha_pago']:
            return Response(
                {'ordenar': 'Solo se puede ordenar por fecha_emision, monto o fecha_pago.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        cobros = cobros.order_by(ordenar, 'id')

        return respuesta_paginada(
            cobros, CobroSerializer,
            request.query_params.get('page', 1)
        )

    serializer = CobroSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    datos = serializer.validated_data
    if concepto_repetido(datos['tramite'], datos['concepto']):
        return Response(
            {'error': f"El trámite ya tiene un cobro vigente por el concepto {datos['concepto']}."},
            status=status.HTTP_409_CONFLICT
        )

    serializer.save(registrado_por=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# Qué hace: GET, PUT, PATCH y DELETE /api/cobros/<id>/ . Se ve, se edita o se borra un cobro.
# Qué usa: validar_rol, select_related, CobroSerializer y concepto_repetido.
# Cómo lo hace: Se busca el cobro (404 si no existe). RN-14: si ya está PAGADO o ANULADO no se
#     puede editar ni borrar (409). Al editar se revisa otra vez que el concepto no quede repetido
#     (409).
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def cobro_detalle_api(request, id):
    error = validar_rol(request)
    if error:
        return error

    try:
        cobro = Cobro.objects.select_related('tramite__carga__cliente', 'registrado_por').get(id=id)
    except Cobro.DoesNotExist:
        return Response({'error': 'Cobro no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(CobroSerializer(cobro).data)

    # RN-14: un cobro pagado o anulado queda cerrado
    if cobro.estado != Cobro.Estado.PENDIENTE:
        return Response(
            {'error': 'Un cobro pagado o anulado no se puede modificar ni eliminar.'},
            status=status.HTTP_409_CONFLICT
        )

    if request.method in ['PUT', 'PATCH']:
        serializer = CobroSerializer(cobro, data=request.data, partial=request.method == 'PATCH')
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        concepto = serializer.validated_data.get('concepto', cobro.concepto)
        if concepto_repetido(cobro.tramite, concepto, excluir_id=cobro.id):
            return Response(
                {'error': f'El trámite ya tiene un cobro vigente por el concepto {concepto}.'},
                status=status.HTTP_409_CONFLICT
            )

        serializer.save()
        return Response(serializer.data)

    cobro.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# Qué hace: POST /api/cobros/<id>/registrar-pago/ con {"metodo_pago": "TRANSFERENCIA"}. Se marca el
#     cobro como pagado.
# Qué usa: validar_rol con ESCRITURA, RegistrarPagoSerializer y timezone.now().
# Cómo lo hace: Solo Administrador y Operador. Si el cobro ya no está pendiente se responde 409. Se
#     valida el método de pago, se cambia el estado a PAGADO y la fecha de pago se pone sola con la
#     fecha y hora de ese momento.
@api_view(['POST'])
def cobro_registrar_pago_api(request, id):
    error = validar_rol(request, ESCRITURA)
    if error:
        return error

    try:
        cobro = Cobro.objects.get(id=id)
    except Cobro.DoesNotExist:
        return Response({'error': 'Cobro no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    if cobro.estado != Cobro.Estado.PENDIENTE:
        return Response({'error': 'El cobro ya fue pagado o anulado.'}, status=status.HTTP_409_CONFLICT)

    serializer = RegistrarPagoSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    cobro.estado = Cobro.Estado.PAGADO
    cobro.metodo_pago = serializer.validated_data['metodo_pago']
    cobro.fecha_pago = timezone.now()  # decisión automática
    cobro.save()
    return Response(CobroSerializer(cobro).data)


# Qué hace: POST /api/cobros/<id>/anular/ . Se anula un cobro. Solo lo puede hacer el
#     Administrador.
# Qué usa: validar_rol con SOLO_ADMIN y el modelo Cobro.
# Cómo lo hace: Se busca el cobro (404). Solo se pueden anular cobros pendientes (si no, 409). Se
#     cambia el estado a ANULADO y se guarda.
@api_view(['POST'])
def cobro_anular_api(request, id):
    error = validar_rol(request, SOLO_ADMIN)
    if error:
        return error

    try:
        cobro = Cobro.objects.get(id=id)
    except Cobro.DoesNotExist:
        return Response({'error': 'Cobro no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    if cobro.estado != Cobro.Estado.PENDIENTE:
        return Response({'error': 'Solo se pueden anular cobros pendientes.'}, status=status.HTTP_409_CONFLICT)

    cobro.estado = Cobro.Estado.ANULADO
    cobro.save()
    return Response(CobroSerializer(cobro).data)
