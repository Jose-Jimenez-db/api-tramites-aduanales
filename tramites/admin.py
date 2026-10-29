from django.contrib import admin

from .models import PermisoTramite, TipoPermiso, Tramite


@admin.register(TipoPermiso)
class TipoPermisoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "institucion", "aplica_a", "activo")
    list_filter = ("aplica_a", "activo")


@admin.register(Tramite)
class TramiteAdmin(admin.ModelAdmin):
    list_display = ("codigo", "carga", "tipo", "estado", "transportista", "fecha_creacion")
    list_filter = ("estado", "tipo")
    search_fields = ("codigo", "carga__numero_contenedor", "carga__cliente__nombre")
    list_select_related = ("carga", "transportista")


@admin.register(PermisoTramite)
class PermisoTramiteAdmin(admin.ModelAdmin):
    list_display = ("tramite", "tipo_permiso", "estado", "numero_resolucion", "fecha_resolucion")
    list_filter = ("estado", "tipo_permiso")
    search_fields = ("tramite__codigo", "tipo_permiso__codigo")
