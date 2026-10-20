from django.contrib import admin

from .models import Transportista


@admin.register(Transportista)
class TransportistaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cedula", "placa_cabezal", "vencimiento_licencia", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "cedula", "placa_cabezal", "numero_licencia")
