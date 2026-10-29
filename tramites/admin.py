from django.contrib import admin

from .models import PermisoTramite, TipoPermiso, Tramite


# Qué hace: Se muestra el catálogo de tipos de permiso en el panel /admin/.
# Qué usa: @admin.register y admin.ModelAdmin.
# Cómo lo hace: Se ponen las columnas (código, nombre, institución, a qué carga aplica y si está
#     activo) y los filtros de la derecha.
@admin.register(TipoPermiso)
class TipoPermisoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "institucion", "aplica_a", "activo")
    list_filter = ("aplica_a", "activo")


# Qué hace: Se muestra la tabla de trámites en el panel /admin/.
# Qué usa: @admin.register y admin.ModelAdmin.
# Cómo lo hace: Se ponen las columnas, los filtros por estado y tipo, y la búsqueda por código,
#     contenedor o nombre del cliente (se usa __ para buscar en otras tablas). list_select_related
#     trae la carga y el transportista en la misma consulta.
@admin.register(Tramite)
class TramiteAdmin(admin.ModelAdmin):
    list_display = ("codigo", "carga", "tipo", "estado", "transportista", "fecha_creacion")
    list_filter = ("estado", "tipo")
    search_fields = ("codigo", "carga__numero_contenedor", "carga__cliente__nombre")
    list_select_related = ("carga", "transportista")


# Qué hace: Se muestran los permisos de cada trámite en el panel /admin/, como una lista aparte.
# Qué usa: @admin.register y admin.ModelAdmin.
# Cómo lo hace: Antes estos permisos salían dentro del trámite con un TabularInline, pero se quitó
#     para dejarlo como en el proyecto de clase. Ahora tienen su propia lista con columnas, filtros
#     y búsqueda.
@admin.register(PermisoTramite)
class PermisoTramiteAdmin(admin.ModelAdmin):
    list_display = ("tramite", "tipo_permiso", "estado", "numero_resolucion", "fecha_resolucion")
    list_filter = ("estado", "tipo_permiso")
    search_fields = ("tramite__codigo", "tipo_permiso__codigo")
