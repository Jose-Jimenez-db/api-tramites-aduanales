from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("cuentas.urls")),
    path("api/", include("clientes.urls")),
    path("api/", include("transportistas.urls")),
    path("api/", include("cargas.urls")),
]

# Respuestas JSON (sin páginas HTML ni trazas) cuando DEBUG=False
handler404 = "core.vistas.no_encontrado"
handler500 = "core.vistas.error_interno"
