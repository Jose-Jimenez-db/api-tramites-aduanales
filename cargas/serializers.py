import re
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import Carga

# Peso máximo de mercancía que admite un contenedor de 40 pies.
PESO_MAXIMO_KG = Decimal("30480")


class CargaSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source="cliente.nombre", read_only=True)

    class Meta:
        model = Carga
        fields = [
            "id", "numero_contenedor", "cliente", "cliente_nombre", "descripcion",
            "tipo", "peso_kg", "buque", "fecha_arribo", "fecha_registro",
        ]
        read_only_fields = ["fecha_registro"]

    def validate_numero_contenedor(self, valor):
        # RN-02: formato ISO 6346, 4 letras mayúsculas y 7 dígitos (ej. MSCU1234567)
        if not re.fullmatch(r"[A-Z]{4}\d{7}", valor):
            raise serializers.ValidationError(
                "El número de contenedor debe tener 4 letras mayúsculas y 7 dígitos (ej. MSCU1234567)."
            )
        return valor

    def validate_peso_kg(self, valor):
        # RN-02: el peso debe estar entre 0,01 kg y 30 480 kg
        if valor <= 0:
            raise serializers.ValidationError("El peso debe ser mayor que 0 kg.")
        if valor > PESO_MAXIMO_KG:
            raise serializers.ValidationError("El peso no puede superar 30 480 kg.")
        return valor

    def validate_fecha_arribo(self, valor):
        # RN-03: la fecha de arribo no puede estar en el futuro.
        if valor > timezone.localdate():
            raise serializers.ValidationError("La fecha de arribo no puede ser futura.")
        return valor

    def validate_cliente(self, cliente):
        # RN-04: un cliente inactivo no puede registrar cargas nuevas.
        cambia_cliente = self.instance is None or self.instance.cliente_id != cliente.id
        if cambia_cliente and not cliente.activo:
            raise serializers.ValidationError("El cliente está inactivo y no puede registrar cargas.")
        return cliente

    def validate(self, attrs):
        # RN-06: una carga que ya tiene trámites no puede cambiar de cliente
        # (protege el invariante también en PATCH).
        if self.instance and "cliente" in attrs:
            if attrs["cliente"].id != self.instance.cliente_id and self.instance.tramites.exists():
                raise serializers.ValidationError(
                    {"cliente": "No se puede cambiar el cliente de una carga que ya tiene trámites."}
                )
        return attrs
