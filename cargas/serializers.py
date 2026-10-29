import re
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import Carga

# Peso máximo de mercancía que admite un contenedor de 40 pies.
PESO_MAXIMO_KG = Decimal("30480")


# Qué hace: Se convierte una carga a JSON y se validan sus datos con las reglas RN-02, RN-03, RN-04
#     y RN-06.
# Qué usa: ModelSerializer de DRF, re, Decimal, timezone y la constante PESO_MAXIMO_KG.
# Cómo lo hace: cliente_nombre usa source="cliente.nombre" para mostrar el nombre del cliente
#     sacándolo de la relación. Las validaciones están en los métodos de abajo.
class CargaSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source="cliente.nombre", read_only=True)

    # Qué hace: Se indica el modelo y los campos del serializador.
    # Qué usa: El modelo Carga, fields y read_only_fields.
    # Cómo lo hace: fecha_registro es de solo lectura porque la pone el sistema.
    class Meta:
        model = Carga
        fields = [
            "id", "numero_contenedor", "cliente", "cliente_nombre", "descripcion",
            "tipo", "peso_kg", "buque", "fecha_arribo", "fecha_registro",
        ]
        read_only_fields = ["fecha_registro"]

    # Qué hace: RN-02: se revisa que el contenedor tenga el formato ISO 6346, por ejemplo
    #     MSCU1234567.
    # Qué usa: re.fullmatch.
    # Cómo lo hace: El patrón [A-Z]{4}\d{7} es 4 letras mayúsculas y 7 dígitos. Si no cumple, se da
    #     error 400.
    def validate_numero_contenedor(self, valor):
        # RN-02: formato ISO 6346, 4 letras mayúsculas y 7 dígitos (ej. MSCU1234567)
        if not re.fullmatch(r"[A-Z]{4}\d{7}", valor):
            raise serializers.ValidationError(
                "El número de contenedor debe tener 4 letras mayúsculas y 7 dígitos (ej. MSCU1234567)."
            )
        return valor

    # Qué hace: RN-02: se revisa que el peso sea mayor que 0 y no pase de 30 480 kg.
    # Qué usa: La constante PESO_MAXIMO_KG (el máximo que soporta un contenedor de 40 pies).
    # Cómo lo hace: Si el peso es 0 o menos, o mayor que el máximo, se da error 400. Como es un
    #     validate_ del campo, también se revisa en PATCH.
    def validate_peso_kg(self, valor):
        # RN-02: el peso debe estar entre 0,01 kg y 30 480 kg
        if valor <= 0:
            raise serializers.ValidationError("El peso debe ser mayor que 0 kg.")
        if valor > PESO_MAXIMO_KG:
            raise serializers.ValidationError("El peso no puede superar 30 480 kg.")
        return valor

    # Qué hace: RN-03: se revisa que la fecha de arribo no sea en el futuro.
    # Qué usa: timezone.localdate().
    # Cómo lo hace: Si la fecha es mayor que hoy se da error 400, porque un barco no puede haber
    #     llegado mañana.
    def validate_fecha_arribo(self, valor):
        # RN-03: la fecha de arribo no puede estar en el futuro.
        if valor > timezone.localdate():
            raise serializers.ValidationError("La fecha de arribo no puede ser futura.")
        return valor

    # Qué hace: RN-04: no se deja registrar cargas a un cliente inactivo.
    # Qué usa: self.instance y el campo activo del cliente.
    # Cómo lo hace: Se revisa solo si es una carga nueva o si se le está cambiando el cliente. Si
    #     ese cliente está inactivo, se da error 400.
    def validate_cliente(self, cliente):
        # RN-04: un cliente inactivo no puede registrar cargas nuevas.
        cambia_cliente = self.instance is None or self.instance.cliente_id != cliente.id
        if cambia_cliente and not cliente.activo:
            raise serializers.ValidationError("El cliente está inactivo y no puede registrar cargas.")
        return cliente

    # Qué hace: RN-06: no se deja cambiar el cliente de una carga que ya tiene trámites.
    # Qué usa: self.instance y la relación tramites de la carga.
    # Cómo lo hace: Si se está editando y viene un cliente distinto, se revisa si la carga ya tiene
    #     trámites. Si tiene, se da error 400. Funciona también en PATCH.
    def validate(self, attrs):
        # RN-06: una carga que ya tiene trámites no puede cambiar de cliente
        # (protege el invariante también en PATCH).
        if self.instance and "cliente" in attrs:
            if attrs["cliente"].id != self.instance.cliente_id and self.instance.tramites.exists():
                raise serializers.ValidationError(
                    {"cliente": "No se puede cambiar el cliente de una carga que ya tiene trámites."}
                )
        return attrs
