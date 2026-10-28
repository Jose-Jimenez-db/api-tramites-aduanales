"""
Lógica de negocio de los trámites.

Las vistas llaman a estas funciones para que las reglas queden en un solo lugar:
    solicitud -> vista -> serializador (valida datos) -> servicio (reglas) -> ORM -> respuesta
"""
from django.db import transaction
from django.utils import timezone

from cobros.models import Cobro

from .models import PermisoTramite, TipoPermiso, Tramite


def asignar_permisos_requeridos(tramite):
    """
    Decisión automática: al crear un trámite se le asignan los permisos que
    exige el tipo de carga (por ejemplo, una carga REFRIGERADA necesita
    certificado fitosanitario y permiso sanitario, además del DUA).
    """
    tipos = TipoPermiso.objects.filter(activo=True, aplica_a__in=["TODAS", tramite.carga.tipo])
    for tipo in tipos:
        PermisoTramite.objects.create(tramite=tramite, tipo_permiso=tipo)


def tramite_activo_de_carga(carga, excluir_id=None):
    """RN-07: devuelve el trámite activo de la carga, o None si no tiene."""
    tramites = Tramite.objects.filter(carga=carga, estado__in=Tramite.ESTADOS_ACTIVOS)
    if excluir_id:
        tramites = tramites.exclude(id=excluir_id)
    return tramites.first()


def validar_cambio_estado(tramite, nuevo_estado):
    """
    Revisa la máquina de estados y las reglas RN-09, RN-10 y RN-11.
    Devuelve (codigo_http, mensaje) si el cambio NO se permite, o None si se puede.
    """
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


@transaction.atomic
def cambiar_estado(tramite, nuevo_estado):
    """Guarda el nuevo estado (llamar solo después de validar_cambio_estado)."""
    if nuevo_estado == Tramite.Estado.LIBERADO:
        tramite.fecha_liberacion = timezone.now()
    if nuevo_estado == Tramite.Estado.CANCELADO:
        # Decisión automática: al cancelar, los cobros pendientes se anulan.
        tramite.cobros.filter(estado=Cobro.Estado.PENDIENTE).update(estado=Cobro.Estado.ANULADO)
    tramite.estado = nuevo_estado
    tramite.save()
