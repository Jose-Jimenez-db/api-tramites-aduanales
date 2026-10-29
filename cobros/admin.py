from django.contrib import admin

from .models import Cobro


# Qué hace: Se muestra la tabla de cobros en el panel /admin/.
# Qué usa: @admin.register y admin.ModelAdmin.
# Cómo lo hace: Se ponen las columnas, los filtros por estado y concepto, y la búsqueda por factura
#     o por código del trámite. list_select_related trae el trámite en la misma consulta.
@admin.register(Cobro)
class CobroAdmin(admin.ModelAdmin):
    list_display = ("numero_factura", "tramite", "concepto", "monto", "estado", "fecha_pago")
    list_filter = ("estado", "concepto")
    search_fields = ("numero_factura", "tramite__codigo")
    list_select_related = ("tramite",)
