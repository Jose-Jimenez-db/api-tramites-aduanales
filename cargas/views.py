from rest_framework import viewsets

from .filters import CargaFilter
from .models import Carga
from .serializers import CargaSerializer


class CargaViewSet(viewsets.ModelViewSet):
    """CRUD de cargas (contenedores)."""

    # select_related evita una consulta extra por cada carga al leer el cliente
    queryset = Carga.objects.select_related("cliente")
    serializer_class = CargaSerializer
    filterset_class = CargaFilter
    search_fields = ["numero_contenedor", "descripcion", "buque", "cliente__nombre"]
    ordering_fields = ["fecha_arribo", "peso_kg", "numero_contenedor"]
    ordering = ["-fecha_arribo"]
