import re

from rest_framework import serializers

from .models import Transportista


# Qué hace: Se convierte un transportista a JSON y se validan sus datos.
# Qué usa: ModelSerializer de DRF y re para los formatos.
# Cómo lo hace: licencia_vigente se declara como BooleanField de solo lectura para mostrar el valor
#     del @property del modelo en la respuesta.
class TransportistaSerializer(serializers.ModelSerializer):
    licencia_vigente = serializers.BooleanField(read_only=True)

    # Qué hace: Se indica el modelo y los campos del serializador.
    # Qué usa: El modelo Transportista, fields y read_only_fields.
    # Cómo lo hace: fecha_registro es de solo lectura porque la pone el sistema.
    class Meta:
        model = Transportista
        fields = [
            "id", "cedula", "nombre", "telefono", "numero_licencia",
            "vencimiento_licencia", "licencia_vigente", "placa_cabezal",
            "activo", "fecha_registro",
        ]
        read_only_fields = ["fecha_registro"]

    # Qué hace: Se revisa que la cédula física tenga el formato 1-1234-5678.
    # Qué usa: re.fullmatch.
    # Cómo lo hace: El patrón \d-\d{4}-\d{4} es 1 dígito, guion, 4 dígitos, guion y 4 dígitos. Si
    #     no cumple, 400.
    def validate_cedula(self, valor):
        if not re.fullmatch(r"\d-\d{4}-\d{4}", valor):
            raise serializers.ValidationError("La cédula debe tener el formato 1-1234-5678.")
        return valor

    # Qué hace: Se revisa que el teléfono tenga el formato 8888-9999.
    # Qué usa: re.fullmatch.
    # Cómo lo hace: Se usa el patrón \d{4}-\d{4}. Si no cumple, se da error 400.
    def validate_telefono(self, valor):
        if not re.fullmatch(r"\d{4}-\d{4}", valor):
            raise serializers.ValidationError("El teléfono debe tener el formato 8888-9999.")
        return valor

    # Qué hace: Se revisa que la placa del cabezal tenga el formato C-123456.
    # Qué usa: re.fullmatch.
    # Cómo lo hace: El patrón C-\d{5,6} es la letra C, guion y de 5 a 6 dígitos. Si no cumple, se
    #     da error 400.
    def validate_placa_cabezal(self, valor):
        if not re.fullmatch(r"C-\d{5,6}", valor):
            raise serializers.ValidationError("La placa del cabezal debe tener el formato C-123456.")
        return valor

    # Qué hace: Se revisa que el nombre tenga al menos 3 letras.
    # Qué usa: strip() y len().
    # Cómo lo hace: Se quitan los espacios de los lados y, si quedan menos de 3 caracteres, se da
    #     error.
    def validate_nombre(self, valor):
        valor = valor.strip()
        if len(valor) < 3:
            raise serializers.ValidationError("El nombre debe tener al menos 3 caracteres.")
        return valor
