from django.core.paginator import Paginator
from django.db.models import Count, ProtectedError, Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from cuentas.permisos import validar_rol

from .models import Cliente
from .serializers import ClienteSerializer


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
def clientes_api(request):
    error = validar_rol(request)
    if error:
        return error

    if request.method == 'GET':
        # annotate agrega la cantidad de cargas de cada cliente
        clientes = Cliente.objects.annotate(cantidad_cargas=Count('cargas')).order_by('nombre')
        activo = request.query_params.get('activo')
        buscar = request.query_params.get('buscar')

        if activo is not None:
            if activo.lower() not in ['true', 'false']:
                return Response(
                    {'activo': 'Utilice true o false.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            clientes = clientes.filter(activo=activo.lower() == 'true')
        if buscar:
            clientes = clientes.filter(
                Q(nombre__icontains=buscar) |
                Q(cedula_juridica__icontains=buscar) |
                Q(correo__icontains=buscar)
            )

        return respuesta_paginada(
            clientes, ClienteSerializer,
            request.query_params.get('page', 1)
        )

    serializer = ClienteSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def cliente_detalle_api(request, id):
    error = validar_rol(request)
    if error:
        return error

    try:
        cliente = Cliente.objects.annotate(cantidad_cargas=Count('cargas')).get(id=id)
    except Cliente.DoesNotExist:
        return Response({'error': 'Cliente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(ClienteSerializer(cliente).data)

    if request.method in ['PUT', 'PATCH']:
        serializer = ClienteSerializer(
            cliente, data=request.data,
            partial=request.method == 'PATCH'
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        cliente.delete()
    except ProtectedError:
        # on_delete=PROTECT: el cliente tiene cargas registradas
        return Response(
            {'error': 'No se puede eliminar un cliente que tiene cargas registradas.'},
            status=status.HTTP_409_CONFLICT
        )
    return Response(status=status.HTTP_204_NO_CONTENT)
