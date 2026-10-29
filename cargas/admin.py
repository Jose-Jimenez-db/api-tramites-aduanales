from django.contrib import admin

from .models import Carga


# Qué hace: Se muestra la tabla de cargas en el panel /admin/.
# Qué usa: @admin.register y admin.ModelAdmin.
# Cómo lo hace: Se ponen las columnas, el filtro por tipo y la búsqueda. list_select_related trae
#     el cliente en la misma consulta para que la lista no haga una consulta por cada fila.
@admin.register(Carga)
class CargaAdmin(admin.ModelAdmin):
    list_display = ("numero_contenedor", "cliente", "tipo", "peso_kg", "fecha_arribo")
    list_filter = ("tipo",)
    search_fields = ("numero_contenedor", "descripcion", "cliente__nombre")
    list_select_related = ("cliente",)
