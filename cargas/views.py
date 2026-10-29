from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.db.models import ProtectedError, Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from cuentas.permisos import validar_rol

from .models import Carga
from .serializers import CargaSerializer


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


# Qué hace: GET y POST /api/cargas/ . Se listan las cargas con filtros, búsqueda y orden, o se crea
#     una.
# Qué usa: validar_rol, select_related, Q, Decimal, InvalidOperation, CargaSerializer y
#     respuesta_paginada.
# Cómo lo hace: Se revisa el rol. En GET se traen las cargas con select_related('cliente') para que
#     el cliente venga en la misma consulta (JOIN). Se pueden combinar los filtros ?cliente=,
#     ?tipo=, ?peso_min=, ?cliente_cedula= (filtro por relación: busca en la tabla de clientes) y
#     ?buscar=. Si un valor no sirve se responde 400. Para ordenar con ?ordenar= se usa lstrip('-')
#     para quitar el guion (que significa de mayor a menor) y revisar que el campo esté en la lista
#     permitida; se agrega 'id' para desempatar. En POST se valida y se guarda.
@api_view(['GET', 'POST'])
def cargas_api(request):
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


# Qué hace: GET, PUT, PATCH y DELETE /api/cargas/<id>/ . Se ve, se edita o se borra una carga.
# Qué usa: validar_rol, select_related, CargaSerializer y ProtectedError.
# Cómo lo hace: Se busca la carga con su cliente (404 si no existe). GET la devuelve y PUT o PATCH
#     la editan. En DELETE, si la carga ya tiene trámites, el PROTECT lanza ProtectedError y se
#     responde 409.
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
