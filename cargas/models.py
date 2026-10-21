from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

from clientes.models import Cliente

# Formato ISO 6346: 4 letras (dueño + categoría) y 7 dígitos. Ejemplo: MSCU1234567
validar_contenedor = RegexValidator(
    regex=r"^[A-Z]{4}\d{7}$",
    message="El número de contenedor debe tener 4 letras mayúsculas y 7 dígitos (ej. MSCU1234567).",
)

# Peso máximo de mercancía que admite un contenedor de 40 pies.
PESO_MAXIMO_KG = Decimal("30480")


class Carga(models.Model):
    """Contenedor que llega al puerto a nombre de un cliente."""

    class Tipo(models.TextChoices):
        SECA = "SECA", "Carga seca"
        REFRIGERADA = "REFRIGERADA", "Carga refrigerada"
        PELIGROSA = "PELIGROSA", "Mercancía peligrosa"

    numero_contenedor = models.CharField(
        max_length=11, unique=True, validators=[validar_contenedor]
    )
    # PROTECT: no se puede borrar un cliente que ya tiene cargas registradas
    # (se perdería el historial aduanero).
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="cargas")
    descripcion = models.CharField(max_length=200)
    tipo = models.CharField(max_length=12, choices=Tipo.choices, default=Tipo.SECA)
    peso_kg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01"), "El peso debe ser mayor que 0 kg."),
            MaxValueValidator(PESO_MAXIMO_KG, "El peso no puede superar 30 480 kg."),
        ],
    )
    buque = models.CharField(max_length=100)
    fecha_arribo = models.DateField()
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_arribo", "numero_contenedor"]
        verbose_name = "carga"
        verbose_name_plural = "cargas"

    def __str__(self):
        return self.numero_contenedor
