from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cedula_juridica", "correo", "telefono", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "cedula_juridica", "correo")
