from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.db.models import ProtectedError, Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from cuentas.permisos import validar_rol

from .models import Carga
from .serializers import CargaSerializer


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


@api_view(['GET', 'POST'])
def cargas_api(request):
    """
    Filtros combinables:
    ?cliente=1  ?tipo=REFRIGERADA  ?peso_min=10000  ?cliente_cedula=3-101-100001
    ?buscar=texto  ?ordenar=-peso_kg  ?page=2
    """
    error = validar_rol(request)
    if error:
        return error

    if request.method == 'GET':
        # select_related trae el cliente en la misma consulta (JOIN)
        cargas = Carga.objects.select_related('cliente')
        cliente = request.query_params.get('cliente')
        tipo = request.query_params.get('tipo')
        peso_min = request.query_params.get('peso_min')
        cliente_cedula = request.query_params.get('cliente_cedula')
        buscar = request.query_params.get('buscar')
        ordenar = request.query_params.get('ordenar', '-fecha_arribo')

        if cliente:
            if not cliente.isdigit():
                return Response({'cliente': 'Debe ser un número.'}, status=status.HTTP_400_BAD_REQUEST)
            cargas = cargas.filter(cliente_id=cliente)
        if tipo:
            cargas = cargas.filter(tipo=tipo.upper())
        if peso_min:
            try:
                cargas = cargas.filter(peso_kg__gte=Decimal(peso_min))
            except InvalidOperation:
                return Response({'peso_min': 'Debe ser un número.'}, status=status.HTTP_400_BAD_REQUEST)
        if cliente_cedula:
            # Filtro por relación: campo de la tabla de clientes
            cargas = cargas.filter(cliente__cedula_juridica=cliente_cedula)
        if buscar:
            cargas = cargas.filter(
                Q(numero_contenedor__icontains=buscar) |
                Q(descripcion__icontains=buscar) |
                Q(cliente__nombre__icontains=buscar)
            )

        if ordenar.lstrip('-') not in ['fecha_arribo', 'peso_kg', 'numero_contenedor']:
            return Response(
                {'ordenar': 'Solo se puede ordenar por fecha_arribo, peso_kg o numero_contenedor.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        cargas = cargas.order_by(ordenar, 'id')

        return respuesta_paginada(
            cargas, CargaSerializer,
            request.query_params.get('page', 1)
        )

    serializer = CargaSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def carga_detalle_api(request, id):
    error = validar_rol(request)
    if error:
        return error

    try:
        carga = Carga.objects.select_related('cliente').get(id=id)
    except Carga.DoesNotExist:
        return Response({'error': 'Carga no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(CargaSerializer(carga).data)

    if request.method in ['PUT', 'PATCH']:
        serializer = CargaSerializer(
            carga, data=request.data,
            partial=request.method == 'PATCH'
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        carga.delete()
    except ProtectedError:
        # on_delete=PROTECT: la carga tiene trámites
        return Response(
            {'error': 'No se puede eliminar una carga que tiene trámites.'},
            status=status.HTTP_409_CONFLICT
        )
    return Response(status=status.HTTP_204_NO_CONTENT)
