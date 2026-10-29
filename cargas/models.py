from django.db import models

from clientes.models import Cliente


class Carga(models.Model):
    """Contenedor que llega al puerto a nombre de un cliente."""

    class Tipo(models.TextChoices):
        SECA = "SECA", "Carga seca"
        REFRIGERADA = "REFRIGERADA", "Carga refrigerada"
        PELIGROSA = "PELIGROSA", "Mercancía peligrosa"

    numero_contenedor = models.CharField(max_length=11, unique=True)
    # PROTECT: no se puede borrar un cliente que ya tiene cargas registradas
    # (se perdería el historial aduanero).
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="cargas")
    descripcion = models.CharField(max_length=200)
    tipo = models.CharField(max_length=12, choices=Tipo.choices, default=Tipo.SECA)
    peso_kg = models.DecimalField(max_digits=8, decimal_places=2)
    buque = models.CharField(max_length=100)
    fecha_arribo = models.DateField()
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.numero_contenedor
