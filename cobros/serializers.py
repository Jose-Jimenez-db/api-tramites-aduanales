from rest_framework import serializers

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

    def validate_monto(self, valor):
        # RN-13: el monto debe ser mayor que 0
        if valor <= 0:
            raise serializers.ValidationError("El monto debe ser mayor que 0.")
        return valor

    def validate_tramite(self, tramite):
        if self.instance and tramite.id != self.instance.tramite_id:
            raise serializers.ValidationError("Un cobro no se puede trasladar a otro trámite.")
        # RN-13: no se cobra sobre trámites cerrados
        if tramite.estado in Tramite.ESTADOS_CERRADOS:
            raise serializers.ValidationError(
                "No se pueden registrar cobros en un trámite liberado o cancelado."
            )
        return tramite


class RegistrarPagoSerializer(serializers.Serializer):
    metodo_pago = serializers.ChoiceField(choices=Cobro.MetodoPago.choices)
