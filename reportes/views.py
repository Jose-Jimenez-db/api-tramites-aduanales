from datetime import date

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import consultas


class ReporteBase(APIView):
    """Los reportes son de solo lectura: los tres roles pueden verlos (GET)."""


class ResumenClientesView(ReporteBase):
    @extend_schema(
        summary="Resumen financiero por cliente",
        parameters=[OpenApiParameter("solo_con_saldo", bool, description="true = solo clientes con saldo pendiente")],
        responses=dict,
    )
    def get(self, request):
        datos = consultas.resumen_por_cliente()
        if request.query_params.get("solo_con_saldo", "").lower() == "true":
            datos = datos.filter(saldo_pendiente__gt=0)
        return Response(list(datos))


class TramitesPorEstadoView(ReporteBase):
    @extend_schema(summary="Cantidad de trámites por estado y por tipo", responses=dict)
    def get(self, request):
        return Response(consultas.tramites_por_estado())


class ListosParaLiberarView(ReporteBase):
    @extend_schema(summary="Trámites que ya cumplen todo para liberarse", responses=dict)
    def get(self, request):
        tramites = consultas.tramites_listos_para_liberar()
        datos = [
            {
                "id": t.id,
                "codigo": t.codigo,
                "contenedor": t.carga.numero_contenedor,
                "cliente": t.carga.cliente.nombre,
                "transportista": t.transportista.nombre,
                "placa_cabezal": t.transportista.placa_cabezal,
            }
            for t in tramites
        ]
        return Response({"cantidad": len(datos), "tramites": datos})


class _DiasSerializer(serializers.Serializer):
    dias = serializers.IntegerField(min_value=1, max_value=365, default=30)


class LicenciasPorVencerView(ReporteBase):
    @extend_schema(
        summary="Transportistas con licencia por vencer",
        parameters=[OpenApiParameter("dias", int, description="Días hacia adelante (1 a 365, por defecto 30)")],
        responses=dict,
    )
    def get(self, request):
        entrada = _DiasSerializer(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        dias = entrada.validated_data["dias"]
        datos = [
            {
                "id": t.id,
                "nombre": t.nombre,
                "placa_cabezal": t.placa_cabezal,
                "vencimiento_licencia": t.vencimiento_licencia,
                "tramites_activos": t.tramites_activos,
            }
            for t in consultas.licencias_por_vencer(dias)
        ]
        return Response({"dias": dias, "transportistas": datos})


class _RangoFechasSerializer(serializers.Serializer):
    desde = serializers.DateField(required=False)
    hasta = serializers.DateField(required=False)

    def validate(self, attrs):
        hoy = timezone.localdate()
        attrs.setdefault("hasta", hoy)
        attrs.setdefault("desde", date(attrs["hasta"].year, attrs["hasta"].month, 1))
        if attrs["desde"] > attrs["hasta"]:
            raise ValidationError({"desde": "La fecha inicial no puede ser mayor que la final."})
        return attrs


class IngresosView(ReporteBase):
    @extend_schema(
        summary="Ingresos cobrados por concepto en un rango de fechas",
        parameters=[
            OpenApiParameter("desde", date, description="AAAA-MM-DD (por defecto: inicio del mes)"),
            OpenApiParameter("hasta", date, description="AAAA-MM-DD (por defecto: hoy)"),
        ],
        responses=dict,
    )
    def get(self, request):
        entrada = _RangoFechasSerializer(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        desde, hasta = entrada.validated_data["desde"], entrada.validated_data["hasta"]
        resultado = consultas.ingresos_por_concepto(desde, hasta)
        return Response({"desde": desde, "hasta": hasta, **resultado})


class PermisosPendientesView(ReporteBase):
    @extend_schema(summary="Permisos pendientes agrupados por institución", responses=dict)
    def get(self, request):
        datos = [
            {
                "institucion": fila["tipo_permiso__institucion"],
                "permisos_pendientes": fila["cantidad"],
                "tramites_afectados": fila["tramites"],
            }
            for fila in consultas.permisos_pendientes_por_institucion()
        ]
        return Response(datos)
