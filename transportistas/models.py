from django.db import models
from django.utils import timezone


class Transportista(models.Model):
    """Chofer de cabezal que retira los contenedores del puerto."""

    cedula = models.CharField(max_length=11, unique=True)
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=9)
    numero_licencia = models.CharField(max_length=20, unique=True)
    vencimiento_licencia = models.DateField()
    placa_cabezal = models.CharField(max_length=8, unique=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.placa_cabezal})"

    @property
    def licencia_vigente(self):
        return self.vencimiento_licencia >= timezone.localdate()
