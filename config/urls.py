from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("cuentas.urls")),
    path("api/", include("clientes.urls")),
    path("api/", include("transportistas.urls")),
    path("api/", include("cargas.urls")),
    path("api/", include("tramites.urls")),
    path("api/", include("cobros.urls")),
    path("api/reportes/", include("reportes.urls")),
    # Documentación automática de la API (OpenAPI / Swagger)
    path("api/esquema/", SpectacularAPIView.as_view(), name="esquema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="esquema"), name="docs"),
]

# Respuestas JSON (sin páginas HTML ni trazas) cuando DEBUG=False
handler404 = "core.vistas.no_encontrado"
handler500 = "core.vistas.error_interno"
