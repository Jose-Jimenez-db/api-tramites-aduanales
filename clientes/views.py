from django.db.models import Count
from rest_framework import viewsets

from .models import Cliente
from .serializers import ClienteSerializer


class ClienteViewSet(viewsets.ModelViewSet):
    """
    CRUD de clientes.

    Búsqueda:  ?buscar=pacifico   (nombre, cédula o correo)
    Filtro:    ?activo=true
    Orden:     ?ordenar=-cantidad_cargas
    """

    queryset = Cliente.objects.annotate(cantidad_cargas=Count("cargas"))
    serializer_class = ClienteSerializer
    filterset_fields = ["activo"]
    search_fields = ["nombre", "cedula_juridica", "correo"]
    ordering_fields = ["nombre", "fecha_registro", "cantidad_cargas"]
    ordering = ["nombre"]
