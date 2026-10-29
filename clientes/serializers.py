import re

from rest_framework import serializers

from tramites.models import Tramite

from .models import Cliente


# Qué hace: Se convierte un cliente a JSON y se validan los datos que llegan para crearlo o
#     editarlo.
# Qué usa: ModelSerializer de DRF, re para revisar formatos y el modelo Tramite para la regla
#     RN-05.
# Cómo lo hace: cantidad_cargas es un campo de solo lectura que viene del annotate de la vista. Las
#     validaciones están en los métodos validate_ de abajo, como en el proyecto de clase.
class ClienteSerializer(serializers.ModelSerializer):
    cantidad_cargas = serializers.IntegerField(read_only=True)

    # Qué hace: Se indica el modelo y los campos del serializador.
    # Qué usa: El modelo Cliente, fields y read_only_fields.
    # Cómo lo hace: fecha_registro va en read_only_fields: sale en la respuesta, pero si alguien la
    #     manda se ignora, porque la pone el sistema.
    class Meta:
        model = Cliente
        fields = [
            "id", "cedula_juridica", "nombre", "correo", "telefono",
            "direccion", "activo", "cantidad_cargas", "fecha_registro",
        ]
        read_only_fields = ["fecha_registro"]

    # Qué hace: RN-01: se revisa que la cédula jurídica tenga el formato 3-101-123456.
    # Qué usa: re.fullmatch con una expresión regular.
    # Cómo lo hace: El patrón \d-\d{3}-\d{6} significa 1 dígito, guion, 3 dígitos, guion y 6
    #     dígitos. fullmatch revisa que TODO el texto cumpla; si no, se lanza un error 400.
    def validate_cedula_juridica(self, valor):
        # RN-01: formato de cédula jurídica de Costa Rica
        if not re.fullmatch(r"\d-\d{3}-\d{6}", valor):
            raise serializers.ValidationError("La cédula jurídica debe tener el formato 3-101-123456.")
        return valor

    # Qué hace: Se revisa que el teléfono tenga el formato 2222-3333.
    # Qué usa: re.fullmatch.
    # Cómo lo hace: El patrón \d{4}-\d{4} es 4 dígitos, guion y 4 dígitos. Si no cumple, se da
    #     error 400.
    def validate_telefono(self, valor):
        if not re.fullmatch(r"\d{4}-\d{4}", valor):
            raise serializers.ValidationError("El teléfono debe tener el formato 2222-3333.")
        return valor

    # Qué hace: Se revisa que el nombre tenga al menos 3 letras.
    # Qué usa: strip() y len().
    # Cómo lo hace: Se quitan los espacios del inicio y del final y se cuenta el largo. Si es menor
    #     que 3 se da error; si no, se devuelve el nombre ya limpio.
    def validate_nombre(self, valor):
        valor = valor.strip()
        if len(valor) < 3:
            raise serializers.ValidationError("El nombre debe tener al menos 3 caracteres.")
        return valor

    # Qué hace: RN-05: no se deja desactivar un cliente que tiene trámites activos.
    # Qué usa: self.instance (el cliente que se está editando) y el modelo Tramite con
    #     ESTADOS_ACTIVOS.
    # Cómo lo hace: Solo se revisa cuando se está editando y llega activo=false. Se busca si hay
    #     trámites activos de cargas de ese cliente (carga__cliente). Si hay, se da error 400. Como
    #     se usa attrs.get, funciona también en PATCH, cuando solo se manda ese campo.
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
