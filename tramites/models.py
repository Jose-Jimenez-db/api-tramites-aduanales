from django.conf import settings
from django.db import models

from cargas.models import Carga
from transportistas.models import Transportista


class TipoPermiso(models.Model):
    """
    Catálogo de permisos que exigen las instituciones según el tipo de carga.
    Ejemplo: la carga refrigerada necesita certificado fitosanitario.
    """

    class AplicaA(models.TextChoices):
        TODAS = "TODAS", "Todas las cargas"
        SECA = Carga.Tipo.SECA.value, Carga.Tipo.SECA.label
        REFRIGERADA = Carga.Tipo.REFRIGERADA.value, Carga.Tipo.REFRIGERADA.label
        PELIGROSA = Carga.Tipo.PELIGROSA.value, Carga.Tipo.PELIGROSA.label

    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=120)
    institucion = models.CharField(max_length=120)
    aplica_a = models.CharField(max_length=12, choices=AplicaA.choices, default=AplicaA.TODAS)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["codigo"]
        verbose_name = "tipo de permiso"
        verbose_name_plural = "tipos de permiso"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Tramite(models.Model):
    """
    Proceso aduanero de una carga: se registra, se revisa, se aprueba y se libera.
    Es el módulo central: une carga, cliente, transportista, permisos y cobros.
    """

    class Tipo(models.TextChoices):
        IMPORTACION = "IMPORTACION", "Importación"
        EXPORTACION = "EXPORTACION", "Exportación"
        TRANSITO = "TRANSITO", "Tránsito"

    class Estado(models.TextChoices):
        REGISTRADO = "REGISTRADO", "Registrado"
        EN_REVISION = "EN_REVISION", "En revisión"
        APROBADO = "APROBADO", "Aprobado"
        LIBERADO = "LIBERADO", "Liberado"
        CANCELADO = "CANCELADO", "Cancelado"

    # Estados en los que el trámite todavía "está abierto"
    ESTADOS_ACTIVOS = (Estado.REGISTRADO, Estado.EN_REVISION, Estado.APROBADO)
    ESTADOS_CERRADOS = (Estado.LIBERADO, Estado.CANCELADO)

    # Cambios de estado permitidos (máquina de estados)
    TRANSICIONES = {
        Estado.REGISTRADO: (Estado.EN_REVISION, Estado.CANCELADO),
        Estado.EN_REVISION: (Estado.APROBADO, Estado.CANCELADO),
        Estado.APROBADO: (Estado.LIBERADO, Estado.CANCELADO),
        Estado.LIBERADO: (),
        Estado.CANCELADO: (),
    }

    # Se genera automáticamente al guardar: TR-2026-00001
    codigo = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    # PROTECT: una carga con trámites no se puede borrar.
    carga = models.ForeignKey(Carga, on_delete=models.PROTECT, related_name="tramites")
    # PROTECT: para "retirar" a un transportista se desactiva, no se borra.
    transportista = models.ForeignKey(
        Transportista,
        on_delete=models.PROTECT,
        related_name="tramites",
        null=True,
        blank=True,
    )
    tipo = models.CharField(max_length=12, choices=Tipo.choices, default=Tipo.IMPORTACION)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.REGISTRADO)
    # Relación N:M con datos propios (estado de cada permiso) mediante PermisoTramite
    permisos = models.ManyToManyField(
        TipoPermiso, through="PermisoTramite", related_name="tramites", blank=True
    )
    observaciones = models.TextField(blank=True)
    # SET_NULL: si se elimina el usuario, el trámite se conserva.
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tramites_creados",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_liberacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "trámite"
        verbose_name_plural = "trámites"
        indexes = [models.Index(fields=["estado"], name="tramite_estado_idx")]

    def __str__(self):
        return self.codigo or f"Trámite #{self.pk}"

    @property
    def esta_activo(self):
        return self.estado in self.ESTADOS_ACTIVOS

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.codigo:
            self.codigo = f"TR-{self.fecha_creacion.year}-{self.pk:05d}"
            Tramite.objects.filter(pk=self.pk).update(codigo=self.codigo)


class PermisoTramite(models.Model):
    """Tabla intermedia de la relación N:M entre Trámite y TipoPermiso."""

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADO = "APROBADO", "Aprobado"
        RECHAZADO = "RECHAZADO", "Rechazado"

    # CASCADE: el permiso solo existe dentro de su trámite.
    tramite = models.ForeignKey(Tramite, on_delete=models.CASCADE, related_name="permisos_tramite")
    # PROTECT: no se borra un tipo de permiso que ya se usó en trámites.
    tipo_permiso = models.ForeignKey(
        TipoPermiso, on_delete=models.PROTECT, related_name="permisos_tramite"
    )
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    numero_resolucion = models.CharField(max_length=30, blank=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["tipo_permiso__codigo"]
        verbose_name = "permiso del trámite"
        verbose_name_plural = "permisos del trámite"
        constraints = [
            models.UniqueConstraint(
                fields=["tramite", "tipo_permiso"], name="permiso_unico_por_tramite"
            )
        ]

    def __str__(self):
        return f"{self.tramite} - {self.tipo_permiso.codigo} ({self.estado})"
