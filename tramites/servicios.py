"""
Lógica de negocio de los trámites.

Las vistas llaman a estas funciones para que las reglas queden en un solo lugar:
    solicitud -> vista -> serializador (valida datos) -> servicio (reglas) -> ORM -> respuesta
"""
from django.db import transaction
from django.utils import timezone

from cobros.models import Cobro

from .models import PermisoTramite, TipoPermiso, Tramite


# Qué hace: Decisión automática: al crear un trámite se le asignan los permisos que pide su tipo de
#     carga. Por ejemplo, una carga REFRIGERADA recibe el DUA, el certificado fitosanitario y el
#     permiso sanitario.
# Qué usa: Los modelos TipoPermiso y PermisoTramite.
# Cómo lo hace: Se buscan los tipos de permiso activos que aplican a TODAS las cargas o al tipo de
#     la carga del trámite, y por cada uno se crea un PermisoTramite en estado PENDIENTE.
def asignar_permisos_requeridos(tramite):
    tipos = TipoPermiso.objects.filter(activo=True, aplica_a__in=["TODAS", tramite.carga.tipo])
    for tipo in tipos:
        PermisoTramite.objects.create(tramite=tramite, tipo_permiso=tipo)


# Qué hace: RN-07: se busca si la carga ya tiene un trámite activo.
# Qué usa: El modelo Tramite y ESTADOS_ACTIVOS.
# Cómo lo hace: Se filtran los trámites de esa carga que estén abiertos. Si se manda excluir_id se
#     deja por fuera ese trámite (sirve al editar). Se devuelve el primero que encuentre o None.
def tramite_activo_de_carga(carga, excluir_id=None):
    tramites = Tramite.objects.filter(carga=carga, estado__in=Tramite.ESTADOS_ACTIVOS)
    if excluir_id:
        tramites = tramites.exclude(id=excluir_id)
    return tramites.first()


# Qué hace: Se revisa si el trámite puede pasar al estado nuevo, aplicando las reglas RN-09, RN-10
#     y RN-11.
# Qué usa: TRANSICIONES, ESTADOS_CERRADOS, los permisos del trámite, el transportista,
#     licencia_vigente y los cobros.
# Cómo lo hace: Si el trámite ya está cerrado se devuelve 409. RN-09: si el estado nuevo no está en
#     las transiciones permitidas, 400. RN-10: para APROBAR, todos los permisos tienen que estar
#     aprobados; si falta alguno se dice cuál. RN-11: para LIBERAR, tiene que haber un
#     transportista activo con licencia vigente, al menos un cobro y ninguno pendiente. Se devuelve
#     (codigo_http, mensaje) si algo falla, o None si se puede.
def validar_cambio_estado(tramite, nuevo_estado):
    if tramite.estado in Tramite.ESTADOS_CERRADOS:
        return 409, f"El trámite ya está {tramite.estado} y no puede cambiar de estado."

    # RN-09: solo se permiten las transiciones definidas
    permitidos = Tramite.TRANSICIONES[tramite.estado]
    if nuevo_estado not in permitidos:
        return 400, (
            f"No se puede pasar de {tramite.estado} a {nuevo_estado}. "
            f"Estados permitidos: {', '.join(permitidos)}."
        )

    # RN-10: para aprobar, todos los permisos deben estar aprobados
    if nuevo_estado == Tramite.Estado.APROBADO:
        faltantes = tramite.permisos_tramite.exclude(estado=PermisoTramite.Estado.APROBADO)
        if faltantes.exists():
            codigos = [p.tipo_permiso.codigo for p in faltantes]
            return 400, f"Faltan permisos por aprobar: {', '.join(codigos)}."

    # RN-11: para liberar, transportista válido y todos los cobros pagados
    if nuevo_estado == Tramite.Estado.LIBERADO:
        transportista = tramite.transportista
        if transportista is None:
            return 400, "Debe asignar un transportista antes de liberar la carga."
        if not transportista.activo or not transportista.licencia_vigente:
            return 400, "El transportista asignado está inactivo o tiene la licencia vencida."

        cobros = tramite.cobros.exclude(estado=Cobro.Estado.ANULADO)
        if not cobros.exists():
            return 400, "El trámite debe tener al menos un cobro registrado."
        if cobros.filter(estado=Cobro.Estado.PENDIENTE).exists():
            return 400, "Todos los cobros deben estar pagados antes de liberar la carga."

    return None


# Qué hace: Se guarda el estado nuevo del trámite. Se llama solo después de validar_cambio_estado.
# Qué usa: @transaction.atomic, timezone.now() y el modelo Cobro.
# Cómo lo hace: Si el estado es LIBERADO se guarda la fecha de liberación. Si es CANCELADO, los
#     cobros pendientes se pasan a ANULADO automáticamente. Al final se guarda el estado. Todo va
#     en una transacción: si algo falla no queda, por ejemplo, un cobro anulado en un trámite que
#     sigue abierto.
@transaction.atomic
def cambiar_estado(tramite, nuevo_estado):
    if nuevo_estado == Tramite.Estado.LIBERADO:
        tramite.fecha_liberacion = timezone.now()
    if nuevo_estado == Tramite.Estado.CANCELADO:
        # Decisión automática: al cancelar, los cobros pendientes se anulan.
        tramite.cobros.filter(estado=Cobro.Estado.PENDIENTE).update(estado=Cobro.Estado.ANULADO)
    tramite.estado = nuevo_estado
    tramite.save()
