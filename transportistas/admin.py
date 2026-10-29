from django.contrib import admin

from .models import Transportista


# Qué hace: Se muestra la tabla de transportistas en el panel /admin/.
# Qué usa: @admin.register y admin.ModelAdmin.
# Cómo lo hace: Se ponen las columnas (list_display), el filtro por activo (list_filter) y los
#     campos de búsqueda (search_fields).
@admin.register(Transportista)
class TransportistaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cedula", "placa_cabezal", "vencimiento_licencia", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "cedula", "placa_cabezal", "numero_licencia")
