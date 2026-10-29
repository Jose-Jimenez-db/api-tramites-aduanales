import re

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

    def validate_cedula(self, valor):
        if not re.fullmatch(r"\d-\d{4}-\d{4}", valor):
            raise serializers.ValidationError("La cédula debe tener el formato 1-1234-5678.")
        return valor

    def validate_telefono(self, valor):
        if not re.fullmatch(r"\d{4}-\d{4}", valor):
            raise serializers.ValidationError("El teléfono debe tener el formato 8888-9999.")
        return valor

    def validate_placa_cabezal(self, valor):
        if not re.fullmatch(r"C-\d{5,6}", valor):
            raise serializers.ValidationError("La placa del cabezal debe tener el formato C-123456.")
        return valor

    def validate_nombre(self, valor):
        valor = valor.strip()
        if len(valor) < 3:
            raise serializers.ValidationError("El nombre debe tener al menos 3 caracteres.")
        return valor
