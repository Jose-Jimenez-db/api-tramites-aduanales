from django.db import models
from django.utils import timezone


# Qué hace: Se crea la tabla de transportistas: los choferes de cabezal que retiran los
#     contenedores.
# Qué usa: models.Model de Django y timezone para la fecha de hoy.
# Cómo lo hace: La cédula, el número de licencia y la placa llevan unique=True para que no se
#     repitan. vencimiento_licencia es una fecha y activo sirve para "retirar" a un chofer sin
#     borrarlo.
class Transportista(models.Model):
    cedula = models.CharField(max_length=11, unique=True)
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=9)
    numero_licencia = models.CharField(max_length=20, unique=True)
    vencimiento_licencia = models.DateField()
    placa_cabezal = models.CharField(max_length=8, unique=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Qué hace: Se define cómo se ve un transportista como texto.
    # Qué usa: Un f-string.
    # Cómo lo hace: Se devuelve el nombre con la placa del cabezal entre paréntesis.
    def __str__(self):
        return f"{self.nombre} ({self.placa_cabezal})"

    # Qué hace: Se dice si la licencia del chofer sigue vigente (True o False).
    # Qué usa: @property y timezone.localdate().
    # Cómo lo hace: Se compara la fecha de vencimiento con la fecha de hoy. Con @property se usa
    #     como si fuera un campo (transportista.licencia_vigente, sin paréntesis), pero NO se
    #     guarda en la base de datos: se calcula cada vez, porque una licencia vigente hoy puede
    #     vencer mañana.
    @property
    def licencia_vigente(self):
        return self.vencimiento_licencia >= timezone.localdate()
