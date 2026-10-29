"""
Rutas principales del proyecto.

Cada módulo tiene su propio urls.py con path(); aquí se incluyen con include().
"""
from django.contrib import admin
from django.urls import include, path

from tramites.views import tipo_permiso_detalle_api, tipos_permiso_api

# Qué hace: Se definen las rutas principales del proyecto: el admin y las rutas de cada app con
#     include().
# Qué usa: path() e include() de Django.
# Cómo lo hace: Cada path une una dirección con la vista que la atiende. <int:id> toma el número de
#     la URL y se lo pasa a la vista como id. Así se hacen las rutas a mano, sin routers, como
#     pidió el profesor.
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
