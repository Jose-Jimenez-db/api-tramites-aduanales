from django.contrib import admin

from .models import Carga


@admin.register(Carga)
class CargaAdmin(admin.ModelAdmin):
    list_display = ("numero_contenedor", "cliente", "tipo", "peso_kg", "fecha_arribo")
    list_filter = ("tipo",)
    search_fields = ("numero_contenedor", "descripcion", "cliente__nombre")
    list_select_related = ("cliente",)
