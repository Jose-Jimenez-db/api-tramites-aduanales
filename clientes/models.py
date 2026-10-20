from django.core.validators import RegexValidator
from django.db import models

validar_cedula_juridica = RegexValidator(
    regex=r"^\d-\d{3}-\d{6}$",
    message="La cédula jurídica debe tener el formato 3-101-123456.",
)
validar_telefono = RegexValidator(
    regex=r"^\d{4}-\d{4}$",
    message="El teléfono debe tener el formato 2222-3333.",
)


class Cliente(models.Model):
    """Empresa importadora o exportadora que contrata a la agencia aduanal."""

    cedula_juridica = models.CharField(
        max_length=12, unique=True, validators=[validar_cedula_juridica]
    )
    nombre = models.CharField(max_length=150)
    correo = models.EmailField(unique=True)
    telefono = models.CharField(max_length=9, validators=[validar_telefono])
    direccion = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "cliente"
        verbose_name_plural = "clientes"

    def __str__(self):
        return f"{self.nombre} ({self.cedula_juridica})"
