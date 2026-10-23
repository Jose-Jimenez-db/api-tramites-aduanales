from datetime import datetime, time, timedelta

import django_filters
from django.utils import timezone

from cargas.models import Carga
from cobros.models import Cobro

from .models import Tramite


def inicio_del_dia(fecha):
    return timezone.make_aware(datetime.combine(fecha, time.min))


class TramiteFilter(django_filters.FilterSet):
    """
    Filtros combinables, por ejemplo:
    /api/tramites/?estado=APROBADO&cliente=2&con_cobros_pendientes=true
    """

    cliente = django_filters.NumberFilter(field_name="carga__cliente")
    tipo_carga = django_filters.ChoiceFilter(field_name="carga__tipo", choices=Carga.Tipo.choices)
    contenedor = django_filters.CharFilter(field_name="carga__numero_contenedor", lookup_expr="icontains")
    creado_desde = django_filters.DateFilter(method="filtrar_creado_desde")
    creado_hasta = django_filters.DateFilter(method="filtrar_creado_hasta")
    con_cobros_pendientes = django_filters.BooleanFilter(method="filtrar_cobros_pendientes")

    class Meta:
        model = Tramite
        fields = ["estado", "tipo", "transportista"]

    # Se usan rangos de fecha y hora (y no __date) para que funcione igual en
    # MySQL aunque el servidor no tenga cargadas las tablas de zonas horarias.
    def filtrar_creado_desde(self, queryset, name, value):
        return queryset.filter(fecha_creacion__gte=inicio_del_dia(value))

    def filtrar_creado_hasta(self, queryset, name, value):
        return queryset.filter(fecha_creacion__lt=inicio_del_dia(value + timedelta(days=1)))

    def filtrar_cobros_pendientes(self, queryset, name, value):
        con_pendientes = queryset.filter(cobros__estado=Cobro.Estado.PENDIENTE).values("pk")
        if value:
            return queryset.filter(pk__in=con_pendientes)
        return queryset.exclude(pk__in=con_pendientes)
