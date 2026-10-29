from django.db import models


# Qué hace: Se crea la tabla de clientes: las empresas que importan o exportan y contratan a la
#     agencia.
# Qué usa: models.Model de Django y sus campos (CharField, EmailField, BooleanField,
#     DateTimeField).
# Cómo lo hace: La cédula jurídica y el correo llevan unique=True para que no se repitan.
#     fecha_registro usa auto_now_add=True, así se llena sola cuando se crea el cliente.
class Cliente(models.Model):
    cedula_juridica = models.CharField(max_length=12, unique=True)
    nombre = models.CharField(max_length=150)
    correo = models.EmailField(unique=True)
    telefono = models.CharField(max_length=9)
    direccion = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Qué hace: Se define cómo se ve un cliente cuando se muestra como texto (por ejemplo en el
    #     admin).
    # Qué usa: Un f-string.
    # Cómo lo hace: Se devuelve el nombre con la cédula entre paréntesis.
    def __str__(self):
        return f"{self.nombre} ({self.cedula_juridica})"
