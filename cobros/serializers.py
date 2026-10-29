from rest_framework import serializers

from tramites.models import Tramite

from .models import Cobro


# Qué hace: Se convierte un cobro a JSON y se validan sus datos con la regla RN-13.
# Qué usa: ModelSerializer, source, SerializerMethodField y el modelo Tramite.
# Cómo lo hace: tramite_codigo y cliente_nombre se sacan de las relaciones con source (el cliente
#     está a dos saltos: cobro -> trámite -> carga -> cliente).
class CobroSerializer(serializers.ModelSerializer):
    tramite_codigo = serializers.CharField(source="tramite.codigo", read_only=True)
    cliente_nombre = serializers.CharField(source="tramite.carga.cliente.nombre", read_only=True)
    registrado_por = serializers.SerializerMethodField()

    # Qué hace: Se indica el modelo, los campos y cuáles son de solo lectura.
    # Qué usa: El modelo Cobro, fields y read_only_fields.
    # Cómo lo hace: El estado y los datos del pago son de solo lectura: solo cambian con las
    #     acciones registrar-pago y anular. Aunque alguien mande estado=PAGADO en un PATCH, se
    #     ignora.
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

    # Qué hace: Se devuelve el usuario que registró el cobro.
    # Qué usa: La relación registrado_por.
    # Cómo lo hace: Si existe se devuelve su username; si no, None.
    def get_registrado_por(self, obj) -> str:
        return obj.registrado_por.username if obj.registrado_por else None

    # Qué hace: RN-13: se revisa que el monto sea mayor que 0.
    # Qué usa: El valor que llega.
    # Cómo lo hace: Si es 0 o negativo se da error 400.
    def validate_monto(self, valor):
        # RN-13: el monto debe ser mayor que 0
        if valor <= 0:
            raise serializers.ValidationError("El monto debe ser mayor que 0.")
        return valor

    # Qué hace: RN-13: no se cobra sobre un trámite cerrado, y un cobro no se puede mover a otro
    #     trámite.
    # Qué usa: self.instance y ESTADOS_CERRADOS del trámite.
    # Cómo lo hace: Si se está editando y viene otro trámite, se da error. Si el trámite está
    #     LIBERADO o CANCELADO, también se da error 400.
    def validate_tramite(self, tramite):
        if self.instance and tramite.id != self.instance.tramite_id:
            raise serializers.ValidationError("Un cobro no se puede trasladar a otro trámite.")
        # RN-13: no se cobra sobre trámites cerrados
        if tramite.estado in Tramite.ESTADOS_CERRADOS:
            raise serializers.ValidationError(
                "No se pueden registrar cobros en un trámite liberado o cancelado."
            )
        return tramite


# Qué hace: Se valida el JSON de la acción registrar-pago.
# Qué usa: serializers.Serializer y ChoiceField con los métodos de pago.
# Cómo lo hace: Solo se acepta un método de pago que exista; si no, 400.
class RegistrarPagoSerializer(serializers.Serializer):
    metodo_pago = serializers.ChoiceField(choices=Cobro.MetodoPago.choices)
