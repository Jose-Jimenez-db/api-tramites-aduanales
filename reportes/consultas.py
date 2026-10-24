"""
Consultas ORM no triviales del proyecto (requisito RF-04).

Cada función devuelve un queryset o un diccionario; las vistas de
reportes/views.py solo validan parámetros y dan formato a la respuesta.
"""
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from clientes.models import Cliente
from cobros.models import Cobro
from tramites.models import PermisoTramite, Tramite
from transportistas.models import Transportista

CERO = Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2))


def resumen_por_cliente():
    """
    Q1 - Agregación con filtros por relación (cliente -> cargas -> trámites -> cobros).
    Por cliente: cantidad de cargas, trámites activos, total facturado y saldo pendiente.
    """
    cobros_vigentes = Q(
        cargas__tramites__cobros__estado__in=[Cobro.Estado.PENDIENTE, Cobro.Estado.PAGADO]
    )
    return (
        Cliente.objects.annotate(
            cantidad_cargas=Count("cargas", distinct=True),
            tramites_activos=Count(
                "cargas__tramites",
                filter=Q(cargas__tramites__estado__in=Tramite.ESTADOS_ACTIVOS),
                distinct=True,
            ),
            total_facturado=Coalesce(
                Sum("cargas__tramites__cobros__monto", filter=cobros_vigentes), CERO
            ),
            saldo_pendiente=Coalesce(
                Sum(
                    "cargas__tramites__cobros__monto",
                    filter=Q(cargas__tramites__cobros__estado=Cobro.Estado.PENDIENTE),
                ),
                CERO,
            ),
        )
        .values(
            "id", "nombre", "cedula_juridica", "cantidad_cargas",
            "tramites_activos", "total_facturado", "saldo_pendiente",
        )
        .order_by("-saldo_pendiente", "nombre")
    )


def tramites_por_estado():
    """Q2 - Agrupación (GROUP BY) de trámites por estado y por tipo."""
    por_estado = Tramite.objects.values("estado").annotate(cantidad=Count("id")).order_by("estado")
    por_tipo = Tramite.objects.values("tipo").annotate(cantidad=Count("id")).order_by("tipo")
    return {"por_estado": list(por_estado), "por_tipo": list(por_tipo)}


def tramites_listos_para_liberar():
    """
    Q3 - Filtros por relaciones + select_related.
    Trámites APROBADOS, con transportista activo y licencia vigente,
    con al menos un cobro pagado y sin cobros pendientes.
    """
    hoy = timezone.localdate()
    con_pendientes = Cobro.objects.filter(estado=Cobro.Estado.PENDIENTE).values("tramite_id")
    con_pagados = Cobro.objects.filter(estado=Cobro.Estado.PAGADO).values("tramite_id")
    return (
        Tramite.objects.filter(
            estado=Tramite.Estado.APROBADO,
            transportista__activo=True,
            transportista__vencimiento_licencia__gte=hoy,
            pk__in=con_pagados,
        )
        .exclude(pk__in=con_pendientes)
        .select_related("carga__cliente", "transportista")
        .order_by("fecha_creacion")
    )


def licencias_por_vencer(dias):
    """
    Q4 - Agregación condicional: transportistas activos cuya licencia vence en
    los próximos `dias` días, con la cantidad de trámites activos asignados.
    """
    hoy = timezone.localdate()
    return (
        Transportista.objects.filter(
            activo=True,
            vencimiento_licencia__gte=hoy,
            vencimiento_licencia__lte=hoy + timedelta(days=dias),
        )
        .annotate(
            tramites_activos=Count("tramites", filter=Q(tramites__estado__in=Tramite.ESTADOS_ACTIVOS))
        )
        .order_by("vencimiento_licencia")
    )


def ingresos_por_concepto(desde, hasta):
    """Q5 - Agregación de cobros pagados en un rango de fechas, agrupada por concepto."""
    inicio = timezone.make_aware(datetime.combine(desde, time.min))
    fin = timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min))
    pagados = Cobro.objects.filter(
        estado=Cobro.Estado.PAGADO, fecha_pago__gte=inicio, fecha_pago__lt=fin
    )
    detalle = (
        pagados.values("concepto")
        .annotate(cantidad=Count("id"), total=Sum("monto"))
        .order_by("-total")
    )
    totales = pagados.aggregate(cantidad=Count("id"), total=Coalesce(Sum("monto"), CERO))
    return {"detalle": list(detalle), **totales}


def permisos_pendientes_por_institucion():
    """
    Q6 - Agrupación por un campo de otra tabla (tipo_permiso__institucion),
    solo de trámites que siguen activos.
    """
    return (
        PermisoTramite.objects.filter(
            estado=PermisoTramite.Estado.PENDIENTE,
            tramite__estado__in=Tramite.ESTADOS_ACTIVOS,
        )
        .values("tipo_permiso__institucion")
        .annotate(cantidad=Count("id"), tramites=Count("tramite", distinct=True))
        .order_by("-cantidad")
    )
