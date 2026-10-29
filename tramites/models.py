from django.conf import settings
from django.db import models

from cargas.models import Carga
from transportistas.models import Transportista


# Qué hace: Se crea la tabla del catálogo de permisos que piden las instituciones (DUA, certificado
#     fitosanitario, etc.). Por ejemplo, la carga refrigerada necesita el certificado
#     fitosanitario.
# Qué usa: models.Model y TextChoices.
# Cómo lo hace: El código es único. aplica_a dice a qué tipo de carga le toca el permiso (TODAS o
#     un tipo específico) y activo permite dejar de usarlo sin borrarlo.
class TipoPermiso(models.Model):
    # Qué hace: Se definen las opciones de a qué carga aplica un permiso.
    # Qué usa: TextChoices y los valores de Carga.Tipo.
    # Cómo lo hace: Se agrega TODAS y se reutilizan los mismos valores y textos de los tipos de
    #     carga para que siempre coincidan.
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

    # Qué hace: Se define cómo se ve un tipo de permiso como texto.
    # Qué usa: Un f-string.
    # Cómo lo hace: Se devuelve el código y el nombre, por ejemplo "DUA - Declaración Única
    #     Aduanera".
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


# Qué hace: Se crea la tabla de trámites: el proceso aduanero de una carga (se registra, se revisa,
#     se aprueba y se libera). Es el módulo central porque une carga, cliente, transportista,
#     permisos y cobros.
# Qué usa: models.Model, ForeignKey, ManyToManyField, TextChoices y settings.AUTH_USER_MODEL.
# Cómo lo hace: ESTADOS_ACTIVOS y ESTADOS_CERRADOS agrupan los estados. TRANSICIONES es la máquina
#     de estados: para cada estado dice a cuáles se puede pasar. Llaves foráneas: carga y
#     transportista con PROTECT (no se borra lo que ya tiene trámites) y creado_por con SET_NULL
#     (si se borra el usuario, el trámite se queda). permisos es la relación N:M con TipoPermiso
#     usando la tabla intermedia PermisoTramite. settings.AUTH_USER_MODEL es la forma que
#     recomienda Django para apuntar a la tabla de usuarios.
class Tramite(models.Model):
    # Qué hace: Se definen los tipos de trámite: importación, exportación y tránsito.
    # Qué usa: TextChoices.
    # Cómo lo hace: Cada opción tiene el valor que se guarda y el texto que se muestra.
    class Tipo(models.TextChoices):
        IMPORTACION = "IMPORTACION", "Importación"
        EXPORTACION = "EXPORTACION", "Exportación"
        TRANSITO = "TRANSITO", "Tránsito"

    # Qué hace: Se definen los estados por los que pasa un trámite.
    # Qué usa: TextChoices.
    # Cómo lo hace: El orden normal es REGISTRADO -> EN_REVISION -> APROBADO -> LIBERADO, y se
    #     puede CANCELAR mientras siga abierto.
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

    # Qué hace: Se define cómo se ve un trámite como texto.
    # Qué usa: El campo codigo.
    # Cómo lo hace: Se devuelve el código (TR-2026-00001); si todavía no tiene, se muestra "Trámite
    #     #id".
    def __str__(self):
        return self.codigo or f"Trámite #{self.pk}"

    # Qué hace: Se dice si el trámite sigue abierto (True o False).
    # Qué usa: @property y ESTADOS_ACTIVOS.
    # Cómo lo hace: Se revisa si el estado está en la lista de estados activos. Se usa como un
    #     campo, sin paréntesis. Ojo: por ahora no se usa en ninguna parte, porque el código
    #     compara directamente con ESTADOS_ACTIVOS.
    @property
    def esta_activo(self):
        return self.estado in self.ESTADOS_ACTIVOS

    # Qué hace: Se guarda el trámite y se le genera el código automáticamente (decisión
    #     automática).
    # Qué usa: save() de Django, el id (pk) y update().
    # Cómo lo hace: Primero se guarda normal para que la base de datos le dé un id. Si no tiene
    #     código, se arma TR-<año>-<id con 5 dígitos> y se guarda con update, que actualiza solo
    #     ese campo.
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.codigo:
            self.codigo = f"TR-{self.fecha_creacion.year}-{self.pk:05d}"
            Tramite.objects.filter(pk=self.pk).update(codigo=self.codigo)


# Qué hace: Se crea la tabla intermedia de la relación N:M entre Trámite y TipoPermiso. Guarda cómo
#     va cada permiso dentro de cada trámite.
# Qué usa: models.Model, ForeignKey y TextChoices.
# Cómo lo hace: Además de las dos llaves foráneas guarda datos propios: el estado del permiso, el
#     número de resolución y la fecha. tramite usa CASCADE (si se borra el trámite se borran sus
#     permisos) y tipo_permiso usa PROTECT (no se borra un tipo que ya se usó).
class PermisoTramite(models.Model):
    # Qué hace: Se definen los estados de un permiso: pendiente, aprobado o rechazado.
    # Qué usa: TextChoices.
    # Cómo lo hace: Todo permiso empieza PENDIENTE y se resuelve con la acción resolver-permiso.
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

    # Qué hace: Se agrega una restricción única en la base de datos.
    # Qué usa: models.UniqueConstraint.
    # Cómo lo hace: La combinación trámite + tipo de permiso no se puede repetir, o sea un trámite
    #     no puede tener dos veces el mismo permiso. Es la única class Meta que quedó en los
    #     modelos.
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tramite", "tipo_permiso"], name="permiso_unico_por_tramite"
            )
        ]

    # Qué hace: Se define cómo se ve un permiso de trámite como texto.
    # Qué usa: Un f-string.
    # Cómo lo hace: Se muestra el trámite, el código del permiso y su estado entre paréntesis.
    def __str__(self):
        return f"{self.tramite} - {self.tipo_permiso.codigo} ({self.estado})"
