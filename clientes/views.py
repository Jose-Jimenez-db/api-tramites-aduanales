from django.core.paginator import Paginator
from django.db.models import Count, ProtectedError, Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from cuentas.permisos import validar_rol

from .models import Cliente
from .serializers import ClienteSerializer


# Qué hace: Se arma la respuesta de una lista dividida en páginas de 5, igual que en el proyecto de
#     clase.
# Qué usa: Paginator de Django, el serializador que se le pase y Response.
# Cómo lo hace: Se divide el queryset en páginas de 5, se toma la página que pidió el usuario con
#     ?page= (get_page da la última si el número se pasa), se convierte a JSON y se devuelve con
#     pagina_actual, total_paginas, total_registros y resultados.
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


# Qué hace: GET y POST /api/clientes/ . Se listan los clientes con filtros y búsqueda, o se crea un
#     cliente.
# Qué usa: validar_rol, el modelo Cliente, Count y Q del ORM, ClienteSerializer y
#     respuesta_paginada.
# Cómo lo hace: Primero se revisa el rol. En GET se traen los clientes con
#     annotate(Count('cargas')) para saber cuántas cargas tiene cada uno. Si viene ?activo= se
#     revisa que sea true o false (si no, 400) y se filtra. Si viene ?buscar= se busca en nombre,
#     cédula o correo usando Q con | (que significa "o"). Al final se devuelve paginado. En POST se
#     validan los datos con el serializador: si están bien se guarda y se responde 201, si no 400.
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


# Qué hace: GET, PUT, PATCH y DELETE /api/clientes/<id>/ . Se ve, se edita o se borra un cliente.
# Qué usa: validar_rol, el modelo Cliente con Count, ClienteSerializer y ProtectedError.
# Cómo lo hace: Se revisa el rol (borrar es solo del Administrador) y se busca el cliente; si no
#     existe se responde 404. GET devuelve el cliente. PUT y PATCH lo editan con el serializador
#     (PATCH con partial=True). En DELETE, si el cliente tiene cargas, Django lanza ProtectedError
#     por el on_delete=PROTECT y se responde 409; si no, se borra y se responde 204.
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
