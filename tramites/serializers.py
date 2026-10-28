from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from cobros.models import Cobro

from . import servicios
from .models import PermisoTramite, TipoPermiso, Tramite


class TipoPermisoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoPermiso
        fields = ["id", "codigo", "nombre", "institucion", "aplica_a", "activo"]

    def validate_codigo(self, valor):
        return valor.strip().upper()


class PermisoTramiteSerializer(serializers.ModelSerializer):
    codigo = serializers.CharField(source="tipo_permiso.codigo", read_only=True)
    nombre = serializers.CharField(source="tipo_permiso.nombre", read_only=True)
    institucion = serializers.CharField(source="tipo_permiso.institucion", read_only=True)

    class Meta:
        model = PermisoTramite
        fields = [
            "id", "tipo_permiso", "codigo", "nombre", "institucion",
            "estado", "numero_resolucion", "fecha_resolucion",
        ]
        read_only_fields = fields


class TramiteSerializer(serializers.ModelSerializer):
    contenedor = serializers.CharField(source="carga.numero_contenedor", read_only=True)
    cliente = serializers.IntegerField(source="carga.cliente_id", read_only=True)
    cliente_nombre = serializers.CharField(source="carga.cliente.nombre", read_only=True)
    transportista_nombre = serializers.SerializerMethodField()
    creado_por = serializers.SerializerMethodField()
    permisos = PermisoTramiteSerializer(source="permisos_tramite", many=True, read_only=True)
    resumen_cobros = serializers.SerializerMethodField()

    class Meta:
        model = Tramite
        fields = [
            "id", "codigo", "tipo", "estado", "carga", "contenedor", "cliente",
            "cliente_nombre", "transportista", "transportista_nombre", "observaciones",
            "permisos", "resumen_cobros", "creado_por", "fecha_creacion",
            "fecha_actualizacion", "fecha_liberacion",
        ]
        read_only_fields = ["codigo", "estado", "fecha_creacion", "fecha_actualizacion", "fecha_liberacion"]

    def get_transportista_nombre(self, obj) -> str:
        return obj.transportista.nombre if obj.transportista else None

    def get_creado_por(self, obj) -> str:
        return obj.creado_por.username if obj.creado_por else None

    def get_resumen_cobros(self, obj) -> dict:
        # Usa los cobros ya cargados con prefetch_related (no hace consultas extra)
        total = pagado = Decimal("0")
        for cobro in obj.cobros.all():
            if cobro.estado == Cobro.Estado.ANULADO:
                continue
            total += cobro.monto
            if cobro.estado == Cobro.Estado.PAGADO:
                pagado += cobro.monto
        return {"total": str(total), "pagado": str(pagado), "pendiente": str(total - pagado)}

    def validate_transportista(self, transportista):
        # RN-08: solo transportistas activos y con licencia vigente
        if transportista is None:
            return transportista
        if not transportista.activo:
            raise serializers.ValidationError("El transportista está inactivo.")
        if not transportista.licencia_vigente:
            raise serializers.ValidationError(
                f"La licencia del transportista venció el {transportista.vencimiento_licencia:%d/%m/%Y}."
            )
        return transportista

    def validate(self, attrs):
        instancia = self.instance
        carga = attrs.get("carga")

        if instancia and carga and carga.id != instancia.carga_id and instancia.estado != Tramite.Estado.REGISTRADO:
            raise serializers.ValidationError(
                {"carga": "Solo se puede cambiar la carga de un trámite en estado REGISTRADO."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        tramite = super().create(validated_data)
        servicios.asignar_permisos_requeridos(tramite)
        return tramite


class CambiarEstadoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=Tramite.Estado.choices)


class ResolverPermisoSerializer(serializers.Serializer):
    permiso = serializers.IntegerField(help_text="id del permiso dentro del trámite")
    estado = serializers.ChoiceField(
        choices=[PermisoTramite.Estado.APROBADO, PermisoTramite.Estado.RECHAZADO]
    )
    numero_resolucion = serializers.CharField(required=False, allow_blank=True, default="", max_length=30)

    def validate(self, data):
        # RN-15: para aprobar un permiso se necesita el número de resolución
        if data["estado"] == PermisoTramite.Estado.APROBADO and not data["numero_resolucion"].strip():
            raise serializers.ValidationError(
                {"numero_resolucion": "El número de resolución es obligatorio para aprobar un permiso."}
            )
        return data
