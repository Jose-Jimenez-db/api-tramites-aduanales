from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

validar_cedula_fisica = RegexValidator(
    regex=r"^\d-\d{4}-\d{4}$",
    message="La cédula debe tener el formato 1-1234-5678.",
)
validar_placa_cabezal = RegexValidator(
    regex=r"^C-\d{5,6}$",
    message="La placa del cabezal debe tener el formato C-123456.",
)
validar_telefono = RegexValidator(
    regex=r"^\d{4}-\d{4}$",
    message="El teléfono debe tener el formato 8888-9999.",
)


class Transportista(models.Model):
    """Chofer de cabezal que retira los contenedores del puerto."""

    cedula = models.CharField(max_length=11, unique=True, validators=[validar_cedula_fisica])
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=9, validators=[validar_telefono])
    numero_licencia = models.CharField(max_length=20, unique=True)
    vencimiento_licencia = models.DateField()
    placa_cabezal = models.CharField(
        max_length=8, unique=True, validators=[validar_placa_cabezal]
    )
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "transportista"
        verbose_name_plural = "transportistas"

    def __str__(self):
        return f"{self.nombre} ({self.placa_cabezal})"

    @property
    def licencia_vigente(self):
        return self.vencimiento_licencia >= timezone.localdate()
