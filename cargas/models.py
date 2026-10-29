from django.db import models

from clientes.models import Cliente


# Qué hace: Se crea la tabla de cargas: los contenedores que llegan al puerto a nombre de un
#     cliente.
# Qué usa: models.Model, ForeignKey hacia Cliente, TextChoices y DecimalField.
# Cómo lo hace: numero_contenedor es único. cliente es la llave foránea (relación 1:N: un cliente
#     tiene muchas cargas) con on_delete=PROTECT para no poder borrar un cliente que ya tiene
#     cargas, y related_name="cargas" para poder escribir cliente.cargas. El peso es DecimalField
#     para no perder decimales.
class Carga(models.Model):
    # Qué hace: Se definen los tipos de carga que se aceptan: seca, refrigerada y peligrosa.
    # Qué usa: models.TextChoices de Django.
    # Cómo lo hace: Cada opción tiene el valor que se guarda (SECA) y el texto que se muestra
    #     (Carga seca). El campo tipo solo acepta estos valores.
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

    # Qué hace: Se define cómo se ve una carga como texto.
    # Qué usa: El campo numero_contenedor.
    # Cómo lo hace: Se devuelve el número del contenedor.
    def __str__(self):
        return self.numero_contenedor
