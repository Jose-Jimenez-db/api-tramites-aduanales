from django.contrib import admin

from .models import Cobro


@admin.register(Cobro)
class CobroAdmin(admin.ModelAdmin):
    list_display = ("numero_factura", "tramite", "concepto", "monto", "estado", "fecha_pago")
    list_filter = ("estado", "concepto")
    search_fields = ("numero_factura", "tramite__codigo")
    list_select_related = ("tramite",)
