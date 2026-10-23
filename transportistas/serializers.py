from rest_framework import serializers

from .models import Transportista


class TransportistaSerializer(serializers.ModelSerializer):
    licencia_vigente = serializers.BooleanField(read_only=True)

    class Meta:
        model = Transportista
        fields = [
            "id", "cedula", "nombre", "telefono", "numero_licencia",
            "vencimiento_licencia", "licencia_vigente", "placa_cabezal",
            "activo", "fecha_registro",
        ]
        read_only_fields = ["fecha_registro"]

    def validate_nombre(self, valor):
        valor = valor.strip()
        if len(valor) < 3:
            raise serializers.ValidationError("El nombre debe tener al menos 3 caracteres.")
        return valor
