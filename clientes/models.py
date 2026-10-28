from django.db import models


class Cliente(models.Model):
    """Empresa importadora o exportadora que contrata a la agencia aduanal."""

    cedula_juridica = models.CharField(max_length=12, unique=True)
    nombre = models.CharField(max_length=150)
    correo = models.EmailField(unique=True)
    telefono = models.CharField(max_length=9)
    direccion = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.cedula_juridica})"
