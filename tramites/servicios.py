"""
Lógica de negocio de los trámites.

Las vistas llaman a estas funciones para que las reglas queden en un solo lugar:
    solicitud -> vista -> serializador (valida formato) -> servicio (reglas) -> ORM -> respuesta
"""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from cobros.models import Cobro
from core.excepciones import Conflicto

from .models import PermisoTramite, TipoPermiso, Tramite

E = Tramite.Estado


def asignar_permisos_requeridos(tramite):
    """
    Decisión automática: al crear un trámite se le asignan los permisos que
    exige el tipo de carga (por ejemplo, una carga REFRIGERADA necesita
    certificado fitosanitario y permiso sanitario, además del DUA).
    """
    tipos = TipoPermiso.objects.filter(activo=True, aplica_a__in=["TODAS", tramite.carga.tipo])
    PermisoTramite.objects.bulk_create(
        [PermisoTramite(tramite=tramite, tipo_permiso=tipo) for tipo in tipos]
    )


def cambiar_estado(tramite, nuevo_estado):
    """Aplica la máquina de estados y las reglas RN-09, RN-10 y RN-11."""
    if tramite.estado in Tramite.ESTADOS_CERRADOS:
        raise Conflicto(f"El trámite ya está {tramite.get_estado_display().lower()} y no puede cambiar de estado.")

    # RN-09: solo se permiten las transiciones definidas
    permitidos = Tramite.TRANSICIONES[tramite.estado]
    if nuevo_estado not in permitidos:
        raise ValidationError(
            {
                "estado": (
                    f"No se puede pasar de {tramite.estado} a {nuevo_estado}. "
                    f"Estados permitidos: {', '.join(permitidos)}."
                )
            }
        )

    # RN-10: para aprobar, todos los permisos deben estar aprobados
    if nuevo_estado == E.APROBADO:
        faltantes = list(
            tramite.permisos_tramite.exclude(estado=PermisoTramite.Estado.APROBADO)
            .values_list("tipo_permiso__codigo", flat=True)
        )
        if faltantes:
            raise ValidationError(
                {"estado": f"Faltan permisos por aprobar: {', '.join(faltantes)}."}
            )

    # RN-11: para liberar, transportista válido y todos los cobros pagados
    if nuevo_estado == E.LIBERADO:
        errores = []
        transportista = tramite.transportista
        if transportista is None:
            errores.append("Debe asignar un transportista antes de liberar la carga.")
        elif not transportista.activo or not transportista.licencia_vigente:
            errores.append("El transportista asignado está inactivo o tiene la licencia vencida.")

        cobros = tramite.cobros.exclude(estado=Cobro.Estado.ANULADO)
        if not cobros.exists():
            errores.append("El trámite debe tener al menos un cobro registrado.")
        elif cobros.filter(estado=Cobro.Estado.PENDIENTE).exists():
            errores.append("Todos los cobros deben estar pagados antes de liberar la carga.")

        if errores:
            raise ValidationError({"estado": errores})

    with transaction.atomic():
        if nuevo_estado == E.LIBERADO:
            tramite.fecha_liberacion = timezone.now()
        if nuevo_estado == E.CANCELADO:
            # Decisión automática: al cancelar, los cobros pendientes se anulan.
            tramite.cobros.filter(estado=Cobro.Estado.PENDIENTE).update(estado=Cobro.Estado.ANULADO)
        tramite.estado = nuevo_estado
        tramite.save(update_fields=["estado", "fecha_liberacion", "fecha_actualizacion"])
    return tramite


def resolver_permiso(tramite, permiso, estado, numero_resolucion=""):
    """RN-15: los permisos se resuelven solo con el trámite EN_REVISION."""
    if tramite.estado != E.EN_REVISION:
        raise ValidationError(
            {"estado": "Los permisos solo se pueden resolver cuando el trámite está EN_REVISION."}
        )
    try:
        registro = tramite.permisos_tramite.select_related("tipo_permiso").get(pk=permiso)
    except PermisoTramite.DoesNotExist:
        raise NotFound("El permiso indicado no pertenece a este trámite.")

    if estado == PermisoTramite.Estado.APROBADO and not numero_resolucion.strip():
        raise ValidationError(
            {"numero_resolucion": "El número de resolución es obligatorio para aprobar un permiso."}
        )

    registro.estado = estado
    registro.numero_resolucion = numero_resolucion.strip()
    registro.fecha_resolucion = timezone.now()
    registro.save()
    return registro
