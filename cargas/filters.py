import django_filters

from tramites.models import Tramite

from .models import Carga


class CargaFilter(django_filters.FilterSet):
    """
    Filtros combinables, por ejemplo:
    /api/cargas/?tipo=REFRIGERADA&arribo_desde=2026-10-01&peso_min=10000
    """

    arribo_desde = django_filters.DateFilter(field_name="fecha_arribo", lookup_expr="gte")
    arribo_hasta = django_filters.DateFilter(field_name="fecha_arribo", lookup_expr="lte")
    peso_min = django_filters.NumberFilter(field_name="peso_kg", lookup_expr="gte")
    peso_max = django_filters.NumberFilter(field_name="peso_kg", lookup_expr="lte")
    # Filtro por relación: cédula del cliente
    cliente_cedula = django_filters.CharFilter(field_name="cliente__cedula_juridica")
    sin_tramite_activo = django_filters.BooleanFilter(method="filtrar_sin_tramite_activo")

    class Meta:
        model = Carga
        fields = ["cliente", "tipo"]

    def filtrar_sin_tramite_activo(self, queryset, name, value):
        activas = queryset.filter(tramites__estado__in=Tramite.ESTADOS_ACTIVOS)
        if value:
            return queryset.exclude(pk__in=activas.values("pk"))
        return queryset.filter(pk__in=activas.values("pk"))
