from django.conf import settings
from django.db import models

from tramites.models import Tramite


# Qué hace: Se crea la tabla de cobros: lo que la agencia le cobra al cliente por cada trámite.
# Qué usa: models.Model, ForeignKey, TextChoices, DecimalField y settings.AUTH_USER_MODEL.
# Cómo lo hace: numero_factura es único y lo genera el sistema. tramite usa PROTECT para que un
#     trámite con cobros no se pueda borrar (respaldo contable). El monto es DecimalField para no
#     perder los céntimos. registrado_por usa SET_NULL: si se borra el usuario, el cobro se queda.
class Cobro(models.Model):
    # Qué hace: Se definen los conceptos por los que se cobra.
    # Qué usa: TextChoices.
    # Cómo lo hace: Almacenaje, desalmacenaje, transporte, honorarios e impuestos.
    class Concepto(models.TextChoices):
        ALMACENAJE = "ALMACENAJE", "Almacenaje en puerto"
        DESALMACENAJE = "DESALMACENAJE", "Desalmacenaje"
        TRANSPORTE = "TRANSPORTE", "Transporte terrestre"
        HONORARIOS = "HONORARIOS", "Honorarios de agencia"
        IMPUESTOS = "IMPUESTOS", "Impuestos de importación"

    # Qué hace: Se definen los estados de un cobro.
    # Qué usa: TextChoices.
    # Cómo lo hace: Empieza PENDIENTE y pasa a PAGADO con registrar-pago o a ANULADO con anular.
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PAGADO = "PAGADO", "Pagado"
        ANULADO = "ANULADO", "Anulado"

    # Qué hace: Se definen las formas de pago que se aceptan.
    # Qué usa: TextChoices.
    # Cómo lo hace: Efectivo, transferencia o tarjeta.
    class MetodoPago(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        TARJETA = "TARJETA", "Tarjeta"

    # Se genera automáticamente al guardar: FAC-000001
    numero_factura = models.CharField(
        max_length=20, unique=True, null=True, blank=True, editable=False
    )
    # PROTECT: un trámite con cobros no se puede borrar (respaldo contable).
    tramite = models.ForeignKey(Tramite, on_delete=models.PROTECT, related_name="cobros")
    concepto = models.CharField(max_length=15, choices=Concepto.choices)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    metodo_pago = models.CharField(max_length=15, choices=MetodoPago.choices, blank=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    fecha_pago = models.DateTimeField(null=True, blank=True)
    # SET_NULL: si se elimina el usuario, el cobro se conserva.
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cobros_registrados",
    )

    # Qué hace: Se define cómo se ve un cobro como texto.
    # Qué usa: Un f-string.
    # Cómo lo hace: Se muestra la factura, el concepto y el monto en colones.
    def __str__(self):
        return f"{self.numero_factura or 'Cobro'} - {self.concepto} ₡{self.monto}"

    # Qué hace: Se guarda el cobro y se le genera el número de factura automáticamente.
    # Qué usa: save() de Django, el id (pk) y update().
    # Cómo lo hace: Primero se guarda para tener el id. Si no tiene factura se arma FAC-<id con 6
    #     dígitos> y se guarda con update, solo ese campo.
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.numero_factura:
            self.numero_factura = f"FAC-{self.pk:06d}"
            Cobro.objects.filter(pk=self.pk).update(numero_factura=self.numero_factura)
