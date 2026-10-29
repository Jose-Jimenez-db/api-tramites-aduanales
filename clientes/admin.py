from django.contrib import admin

from .models import Cliente


# Qué hace: Se muestra la tabla de clientes en el panel /admin/.
# Qué usa: @admin.register y admin.ModelAdmin.
# Cómo lo hace: list_display son las columnas que se ven, list_filter el filtro de la derecha y
#     search_fields los campos donde busca la barra de búsqueda.
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cedula_juridica", "correo", "telefono", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "cedula_juridica", "correo")
