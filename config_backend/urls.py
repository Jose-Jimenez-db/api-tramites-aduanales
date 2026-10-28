"""
Rutas principales del proyecto.

Cada módulo tiene su propio urls.py con path(); aquí se incluyen con include().
"""
from django.contrib import admin
from django.urls import include, path

from tramites.views import tipo_permiso_detalle_api, tipos_permiso_api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("cuentas.urls")),
    path("api/clientes/", include("clientes.urls")),
    path("api/transportistas/", include("transportistas.urls")),
    path("api/cargas/", include("cargas.urls")),
    path("api/tipos-permiso/", tipos_permiso_api, name="tipos_permiso_api"),
    path("api/tipos-permiso/<int:id>/", tipo_permiso_detalle_api, name="tipo_permiso_detalle_api"),
    path("api/tramites/", include("tramites.urls")),
    path("api/cobros/", include("cobros.urls")),
    path("api/reportes/", include("reportes.urls")),
]
