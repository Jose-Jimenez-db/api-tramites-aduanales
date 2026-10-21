from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from tramites.models import Tramite


class Cobro(models.Model):
    """Monto que la agencia le cobra al cliente por un trámite."""

    class Concepto(models.TextChoices):
        ALMACENAJE = "ALMACENAJE", "Almacenaje en puerto"
        DESALMACENAJE = "DESALMACENAJE", "Desalmacenaje"
        TRANSPORTE = "TRANSPORTE", "Transporte terrestre"
        HONORARIOS = "HONORARIOS", "Honorarios de agencia"
        IMPUESTOS = "IMPUESTOS", "Impuestos de importación"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PAGADO = "PAGADO", "Pagado"
        ANULADO = "ANULADO", "Anulado"

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
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"), "El monto debe ser mayor que 0.")],
    )
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

    class Meta:
        ordering = ["-fecha_emision"]
        verbose_name = "cobro"
        verbose_name_plural = "cobros"

    def __str__(self):
        return f"{self.numero_factura or 'Cobro'} - {self.concepto} ₡{self.monto}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.numero_factura:
            self.numero_factura = f"FAC-{self.pk:06d}"
            Cobro.objects.filter(pk=self.pk).update(numero_factura=self.numero_factura)
