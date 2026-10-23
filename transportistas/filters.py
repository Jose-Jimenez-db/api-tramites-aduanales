import django_filters
from django.utils import timezone

from .models import Transportista


class TransportistaFilter(django_filters.FilterSet):
    """
    ?activo=true
    ?licencia_vigente=true
    ?vence_antes=2026-12-31
    """

    licencia_vigente = django_filters.BooleanFilter(method="filtrar_licencia_vigente")
    vence_antes = django_filters.DateFilter(field_name="vencimiento_licencia", lookup_expr="lte")

    class Meta:
        model = Transportista
        fields = ["activo"]

    def filtrar_licencia_vigente(self, queryset, name, value):
        hoy = timezone.localdate()
        if value:
            return queryset.filter(vencimiento_licencia__gte=hoy)
        return queryset.filter(vencimiento_licencia__lt=hoy)
