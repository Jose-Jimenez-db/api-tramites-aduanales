from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from cobros.models import Cobro

from . import servicios
from .models import PermisoTramite, TipoPermiso, Tramite


# Qué hace: Se convierte un tipo de permiso del catálogo a JSON y se validan sus datos.
# Qué usa: ModelSerializer de DRF.
# Cómo lo hace: Se usa en las rutas /api/tipos-permiso/.
class TipoPermisoSerializer(serializers.ModelSerializer):
    # Qué hace: Se indica el modelo y los campos del serializador.
    # Qué usa: El modelo TipoPermiso y fields.
    # Cómo lo hace: Se ponen todos los campos del catálogo.
    class Meta:
        model = TipoPermiso
        fields = ["id", "codigo", "nombre", "institucion", "aplica_a", "activo"]

    # Qué hace: Se limpia el código del permiso.
    # Qué usa: strip() y upper().
    # Cómo lo hace: Se quitan los espacios de los lados y se pasa a mayúsculas, así " dua " queda
    #     "DUA".
    def validate_codigo(self, valor):
        return valor.strip().upper()


# Qué hace: Se convierte a JSON cada permiso de un trámite, con los datos de su tipo.
# Qué usa: ModelSerializer y source para leer campos de otra tabla.
# Cómo lo hace: codigo, nombre e institucion salen del tipo de permiso usando
#     source="tipo_permiso.codigo", etc.
class PermisoTramiteSerializer(serializers.ModelSerializer):
    codigo = serializers.CharField(source="tipo_permiso.codigo", read_only=True)
    nombre = serializers.CharField(source="tipo_permiso.nombre", read_only=True)
    institucion = serializers.CharField(source="tipo_permiso.institucion", read_only=True)

    # Qué hace: Se indica el modelo y los campos del serializador.
    # Qué usa: El modelo PermisoTramite, fields y read_only_fields.
    # Cómo lo hace: Todos los campos son de solo lectura porque los permisos solo se cambian con
    #     resolver-permiso.
    class Meta:
        model = PermisoTramite
        fields = [
            "id", "tipo_permiso", "codigo", "nombre", "institucion",
            "estado", "numero_resolucion", "fecha_resolucion",
        ]
        read_only_fields = fields


# Qué hace: Se convierte un trámite a JSON con datos de sus relaciones y se validan los datos al
#     crearlo o editarlo.
# Qué usa: ModelSerializer, source, SerializerMethodField, PermisoTramiteSerializer anidado,
#     Decimal, transaction y servicios.
# Cómo lo hace: contenedor, cliente y cliente_nombre se sacan de la carga con source. permisos es
#     la lista de permisos del trámite usando otro serializador adentro (anidado).
#     transportista_nombre, creado_por y resumen_cobros se calculan con métodos get_.
class TramiteSerializer(serializers.ModelSerializer):
    contenedor = serializers.CharField(source="carga.numero_contenedor", read_only=True)
    cliente = serializers.IntegerField(source="carga.cliente_id", read_only=True)
    cliente_nombre = serializers.CharField(source="carga.cliente.nombre", read_only=True)
    transportista_nombre = serializers.SerializerMethodField()
    creado_por = serializers.SerializerMethodField()
    permisos = PermisoTramiteSerializer(source="permisos_tramite", many=True, read_only=True)
    resumen_cobros = serializers.SerializerMethodField()

    # Qué hace: Se indica el modelo, los campos y cuáles son de solo lectura.
    # Qué usa: El modelo Tramite, fields y read_only_fields.
    # Cómo lo hace: codigo, estado y las fechas son de solo lectura: el código lo genera el sistema
    #     y el estado solo cambia con la acción cambiar-estado.
    class Meta:
        model = Tramite
        fields = [
            "id", "codigo", "tipo", "estado", "carga", "contenedor", "cliente",
            "cliente_nombre", "transportista", "transportista_nombre", "observaciones",
            "permisos", "resumen_cobros", "creado_por", "fecha_creacion",
            "fecha_actualizacion", "fecha_liberacion",
        ]
        read_only_fields = ["codigo", "estado", "fecha_creacion", "fecha_actualizacion", "fecha_liberacion"]

    # Qué hace: Se devuelve el nombre del transportista del trámite.
    # Qué usa: La relación transportista.
    # Cómo lo hace: Si el trámite tiene transportista se devuelve su nombre; si no, None.
    def get_transportista_nombre(self, obj) -> str:
        return obj.transportista.nombre if obj.transportista else None

    # Qué hace: Se devuelve el usuario que creó el trámite.
    # Qué usa: La relación creado_por.
    # Cómo lo hace: Si existe se devuelve su username; si el usuario se borró, None.
    def get_creado_por(self, obj) -> str:
        return obj.creado_por.username if obj.creado_por else None

    # Qué hace: Se calcula cuánto se ha cobrado en el trámite: total, pagado y pendiente.
    # Qué usa: Los cobros del trámite (ya vienen cargados con prefetch_related) y Decimal.
    # Cómo lo hace: Se recorren los cobros, los anulados se saltan, se suma el monto al total y, si
    #     está pagado, también a pagado. El pendiente es total menos pagado. Como los cobros ya
    #     vienen cargados, esto no hace consultas extra.
    def get_resumen_cobros(self, obj) -> dict:
        # Usa los cobros ya cargados con prefetch_related (no hace consultas extra)
        total = pagado = Decimal("0")
        for cobro in obj.cobros.all():
            if cobro.estado == Cobro.Estado.ANULADO:
                continue
            total += cobro.monto
            if cobro.estado == Cobro.Estado.PAGADO:
                pagado += cobro.monto
        return {"total": str(total), "pagado": str(pagado), "pendiente": str(total - pagado)}

    # Qué hace: RN-08: solo se puede asignar un transportista activo y con la licencia vigente.
    # Qué usa: Los campos activo y licencia_vigente del transportista.
    # Cómo lo hace: Si no se manda transportista se deja pasar. Si está inactivo o la licencia
    #     venció se da error 400 con la fecha de vencimiento. Funciona también en PATCH.
    def validate_transportista(self, transportista):
        # RN-08: solo transportistas activos y con licencia vigente
        if transportista is None:
            return transportista
        if not transportista.activo:
            raise serializers.ValidationError("El transportista está inactivo.")
        if not transportista.licencia_vigente:
            raise serializers.ValidationError(
                f"La licencia del transportista venció el {transportista.vencimiento_licencia:%d/%m/%Y}."
            )
        return transportista

    # Qué hace: Se revisa que solo se pueda cambiar la carga de un trámite que está REGISTRADO.
    # Qué usa: self.instance y attrs.
    # Cómo lo hace: Si se está editando, viene una carga distinta y el trámite ya no está
    #     REGISTRADO, se da error 400.
    def validate(self, attrs):
        instancia = self.instance
        carga = attrs.get("carga")

        if instancia and carga and carga.id != instancia.carga_id and instancia.estado != Tramite.Estado.REGISTRADO:
            raise serializers.ValidationError(
                {"carga": "Solo se puede cambiar la carga de un trámite en estado REGISTRADO."}
            )
        return attrs

    # Qué hace: Se crea el trámite y se le asignan sus permisos automáticamente.
    # Qué usa: @transaction.atomic, super().create y servicios.asignar_permisos_requeridos.
    # Cómo lo hace: Se crea el trámite normal y luego se le asignan los permisos según el tipo de
    #     carga. Va en una transacción para que no quede un trámite sin sus permisos si algo falla.
    @transaction.atomic
    def create(self, validated_data):
        tramite = super().create(validated_data)
        servicios.asignar_permisos_requeridos(tramite)
        return tramite


# Qué hace: Se valida el JSON de la acción cambiar-estado.
# Qué usa: serializers.Serializer y ChoiceField con los estados del trámite.
# Cómo lo hace: Solo se acepta un estado que exista; si no, 400. Las reglas de si se puede o no se
#     revisan en servicios.py.
class CambiarEstadoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=Tramite.Estado.choices)


# Qué hace: Se valida el JSON de la acción resolver-permiso.
# Qué usa: serializers.Serializer, IntegerField, ChoiceField y CharField.
# Cómo lo hace: Se pide el id del permiso, el estado (solo APROBADO o RECHAZADO) y el número de
#     resolución, que es opcional aquí pero se revisa abajo.
class ResolverPermisoSerializer(serializers.Serializer):
    permiso = serializers.IntegerField(help_text="id del permiso dentro del trámite")
    estado = serializers.ChoiceField(
        choices=[PermisoTramite.Estado.APROBADO, PermisoTramite.Estado.RECHAZADO]
    )
    numero_resolucion = serializers.CharField(required=False, allow_blank=True, default="", max_length=30)

    # Qué hace: RN-15: para aprobar un permiso se necesita el número de resolución.
    # Qué usa: Los datos ya validados (data).
    # Cómo lo hace: Si el estado es APROBADO y el número de resolución viene vacío, se da error
    #     400.
    def validate(self, data):
        # RN-15: para aprobar un permiso se necesita el número de resolución
        if data["estado"] == PermisoTramite.Estado.APROBADO and not data["numero_resolucion"].strip():
            raise serializers.ValidationError(
                {"numero_resolucion": "El número de resolución es obligatorio para aprobar un permiso."}
            )
        return data
