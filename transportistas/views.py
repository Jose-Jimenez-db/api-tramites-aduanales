from rest_framework import viewsets

from .filters import TransportistaFilter
from .models import Transportista
from .serializers import TransportistaSerializer


class TransportistaViewSet(viewsets.ModelViewSet):
    """CRUD de transportistas (choferes de cabezal)."""

    queryset = Transportista.objects.all()
    serializer_class = TransportistaSerializer
    filterset_class = TransportistaFilter
    search_fields = ["nombre", "cedula", "placa_cabezal", "numero_licencia"]
    ordering_fields = ["nombre", "vencimiento_licencia", "fecha_registro"]
    ordering = ["nombre"]
