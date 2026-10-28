from django.core.paginator import Paginator
from django.db.models import ProtectedError
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from cuentas.permisos import validar_rol

from .models import Transportista
from .serializers import TransportistaSerializer


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
def transportistas_api(request):
    error = validar_rol(request)
    if error:
        return error

    if request.method == 'GET':
        transportistas = Transportista.objects.order_by('nombre')
        activo = request.query_params.get('activo')
        licencia_vigente = request.query_params.get('licencia_vigente')
        hoy = timezone.localdate()

        if activo is not None:
            if activo.lower() not in ['true', 'false']:
                return Response({'activo': 'Utilice true o false.'}, status=status.HTTP_400_BAD_REQUEST)
            transportistas = transportistas.filter(activo=activo.lower() == 'true')
        if licencia_vigente is not None:
            if licencia_vigente.lower() not in ['true', 'false']:
                return Response(
                    {'licencia_vigente': 'Utilice true o false.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if licencia_vigente.lower() == 'true':
                transportistas = transportistas.filter(vencimiento_licencia__gte=hoy)
            else:
                transportistas = transportistas.filter(vencimiento_licencia__lt=hoy)

        return respuesta_paginada(
            transportistas, TransportistaSerializer,
            request.query_params.get('page', 1)
        )

    serializer = TransportistaSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def transportista_detalle_api(request, id):
    error = validar_rol(request)
    if error:
        return error

    try:
        transportista = Transportista.objects.get(id=id)
    except Transportista.DoesNotExist:
        return Response({'error': 'Transportista no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(TransportistaSerializer(transportista).data)

    if request.method in ['PUT', 'PATCH']:
        serializer = TransportistaSerializer(
            transportista, data=request.data,
            partial=request.method == 'PATCH'
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        transportista.delete()
    except ProtectedError:
        # on_delete=PROTECT: el transportista ya tiene trámites asignados
        return Response(
            {'error': 'No se puede eliminar un transportista con trámites. Desactívelo.'},
            status=status.HTTP_409_CONFLICT
        )
    return Response(status=status.HTTP_204_NO_CONTENT)
