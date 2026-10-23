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
