from rest_framework import serializers

from core.excepciones import Conflicto
from tramites.models import Tramite

from .models import Cobro


class CobroSerializer(serializers.ModelSerializer):
    tramite_codigo = serializers.CharField(source="tramite.codigo", read_only=True)
    cliente_nombre = serializers.CharField(source="tramite.carga.cliente.nombre", read_only=True)
    registrado_por = serializers.SerializerMethodField()

    class Meta:
        model = Cobro
        fields = [
            "id", "numero_factura", "tramite", "tramite_codigo", "cliente_nombre",
            "concepto", "monto", "estado", "metodo_pago", "fecha_emision",
            "fecha_pago", "registrado_por",
        ]
        # El estado y los datos del pago solo cambian con las acciones
        # registrar-pago y anular, nunca editando el cobro directamente.
        read_only_fields = ["numero_factura", "estado", "metodo_pago", "fecha_emision", "fecha_pago"]

    def get_registrado_por(self, obj) -> str:
        return obj.registrado_por.username if obj.registrado_por else None

    def validate_tramite(self, tramite):
        if self.instance and tramite.id != self.instance.tramite_id:
            raise serializers.ValidationError("Un cobro no se puede trasladar a otro trámite.")
        # RN-13: no se cobra sobre trámites cerrados
        if tramite.estado in Tramite.ESTADOS_CERRADOS:
            raise serializers.ValidationError(
                "No se pueden registrar cobros en un trámite liberado o cancelado."
            )
        return tramite

    def validate(self, attrs):
        # RN-13: un solo cobro vigente por concepto en cada trámite -> 409
        tramite = attrs.get("tramite", getattr(self.instance, "tramite", None))
        concepto = attrs.get("concepto", getattr(self.instance, "concepto", None))
        repetidos = Cobro.objects.filter(tramite=tramite, concepto=concepto).exclude(
            estado=Cobro.Estado.ANULADO
        )
        if self.instance:
            repetidos = repetidos.exclude(pk=self.instance.pk)
        if repetidos.exists():
            raise Conflicto(f"El trámite ya tiene un cobro vigente por el concepto {concepto}.")
        return attrs


class RegistrarPagoSerializer(serializers.Serializer):
    metodo_pago = serializers.ChoiceField(choices=Cobro.MetodoPago.choices)
