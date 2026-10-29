import re

from rest_framework import serializers

from tramites.models import Tramite

from .models import Cliente


class ClienteSerializer(serializers.ModelSerializer):
    cantidad_cargas = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cliente
        fields = [
            "id", "cedula_juridica", "nombre", "correo", "telefono",
            "direccion", "activo", "cantidad_cargas", "fecha_registro",
        ]
        read_only_fields = ["fecha_registro"]

    def validate_cedula_juridica(self, valor):
        # RN-01: formato de cédula jurídica de Costa Rica
        if not re.fullmatch(r"\d-\d{3}-\d{6}", valor):
            raise serializers.ValidationError("La cédula jurídica debe tener el formato 3-101-123456.")
        return valor

    def validate_telefono(self, valor):
        if not re.fullmatch(r"\d{4}-\d{4}", valor):
            raise serializers.ValidationError("El teléfono debe tener el formato 2222-3333.")
        return valor

    def validate_nombre(self, valor):
        valor = valor.strip()
        if len(valor) < 3:
            raise serializers.ValidationError("El nombre debe tener al menos 3 caracteres.")
        return valor

    def validate(self, attrs):
        # RN-05: no se puede desactivar un cliente con trámites abiertos.
        # Se valida también en PATCH porque solo se envía el campo "activo".
        if self.instance and attrs.get("activo") is False and self.instance.activo:
            tiene_activos = Tramite.objects.filter(
                carga__cliente=self.instance, estado__in=Tramite.ESTADOS_ACTIVOS
            ).exists()
            if tiene_activos:
                raise serializers.ValidationError(
                    {"activo": "No se puede desactivar un cliente con trámites activos."}
                )
        return attrs
