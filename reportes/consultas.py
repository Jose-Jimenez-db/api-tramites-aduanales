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


# Qué hace: Consulta Q1: por cada cliente se calcula cuántas cargas tiene, cuántos trámites
#     activos, cuánto se le ha facturado y cuánto debe.
# Qué usa: annotate, Count, Sum, Q, Coalesce y values del ORM.
# Cómo lo hace: Se recorren las relaciones cliente -> cargas -> trámites -> cobros con __. Count
#     con distinct=True cuenta sin repetir. Sum con filter=Q(...) suma solo los cobros que cumplen
#     (vigentes o pendientes). Coalesce pone 0 en vez de vacío cuando no hay cobros. Se ordena por
#     el saldo pendiente de mayor a menor.
def resumen_por_cliente():
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


# Qué hace: Consulta Q2: se cuenta cuántos trámites hay en cada estado y de cada tipo.
# Qué usa: values, annotate y Count (es como un GROUP BY en SQL).
# Cómo lo hace: values('estado') agrupa por estado y annotate(Count('id')) cuenta cuántos hay en
#     cada grupo. Lo mismo se hace por tipo y se devuelven las dos listas.
def tramites_por_estado():
    por_estado = Tramite.objects.values("estado").annotate(cantidad=Count("id")).order_by("estado")
    por_tipo = Tramite.objects.values("tipo").annotate(cantidad=Count("id")).order_by("tipo")
    return {"por_estado": list(por_estado), "por_tipo": list(por_tipo)}


# Qué hace: Consulta Q3: se buscan los trámites APROBADOS que ya se pueden liberar.
# Qué usa: filter con relaciones, subconsultas con values, pk__in, exclude, select_related y
#     timezone.
# Cómo lo hace: Se piden trámites aprobados con transportista activo y licencia vigente (se filtra
#     por campos del transportista con __), que tengan al menos un cobro pagado (pk__in) y ningún
#     cobro pendiente (exclude). select_related trae la carga, el cliente y el transportista en la
#     misma consulta.
def tramites_listos_para_liberar():
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


# Qué hace: Consulta Q4: transportistas activos cuya licencia vence en los próximos N días, con
#     cuántos trámites activos tienen.
# Qué usa: timedelta, filter, annotate, Count con filter=Q y timezone.
# Cómo lo hace: Se calcula el rango de fechas desde hoy hasta hoy + timedelta(days=dias) y se
#     filtran las licencias que vencen en ese rango. Después se cuentan solo los trámites activos
#     de cada uno y se ordena por la fecha que vence primero.
def licencias_por_vencer(dias):
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


# Qué hace: Consulta Q5: cuánto se cobró (ya pagado) entre dos fechas, separado por concepto y con
#     el total.
# Qué usa: datetime, time, timedelta, make_aware, values, annotate, aggregate, Sum y Coalesce.
# Cómo lo hace: Como fecha_pago tiene hora, se arma el inicio a las 00:00 de la fecha desde y el
#     final a las 00:00 del día siguiente a hasta (hasta + timedelta(days=1)), para incluir todo
#     ese día. Se agrupa por concepto con values + annotate y se saca el total general con
#     aggregate.
def ingresos_por_concepto(desde, hasta):
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


# Qué hace: Consulta Q6: cuántos permisos pendientes tiene cada institución, solo de trámites que
#     siguen abiertos.
# Qué usa: filter, values con un campo de otra tabla, annotate y Count con distinct.
# Cómo lo hace: Se filtran los permisos pendientes de trámites activos y se agrupan por
#     tipo_permiso__institucion, que es un campo de la tabla de tipos de permiso. Se cuentan los
#     permisos y los trámites distintos, y se ordena de mayor a menor.
def permisos_pendientes_por_institucion():
    return (
        PermisoTramite.objects.filter(
            estado=PermisoTramite.Estado.PENDIENTE,
            tramite__estado__in=Tramite.ESTADOS_ACTIVOS,
        )
        .values("tipo_permiso__institucion")
        .annotate(cantidad=Count("id"), tramites=Count("tramite", distinct=True))
        .order_by("-cantidad")
    )
