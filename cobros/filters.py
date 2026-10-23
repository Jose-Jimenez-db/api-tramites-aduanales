import django_filters

from .models import Cobro


class CobroFilter(django_filters.FilterSet):
    """
    Filtros combinables, por ejemplo:
    /api/cobros/?estado=PENDIENTE&cliente=1&monto_min=50000
    """

    cliente = django_filters.NumberFilter(field_name="tramite__carga__cliente")
    monto_min = django_filters.NumberFilter(field_name="monto", lookup_expr="gte")
    monto_max = django_filters.NumberFilter(field_name="monto", lookup_expr="lte")

    class Meta:
        model = Cobro
        fields = ["estado", "concepto", "tramite", "metodo_pago"]
