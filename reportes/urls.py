from django.urls import path

from . import views

# Qué hace: Se definen las 6 rutas de los reportes (van bajo /api/reportes/).
# Qué usa: path() de Django y las vistas de views.py.
# Cómo lo hace: Cada path une una dirección con la vista que la atiende. Así se hacen las rutas a
#     mano, sin routers, como pidió el profesor.
urlpatterns = [
    path("resumen-clientes/", views.resumen_clientes_api, name="reporte_resumen_clientes"),
    path("tramites-por-estado/", views.tramites_por_estado_api, name="reporte_tramites_por_estado"),
    path("listos-para-liberar/", views.listos_para_liberar_api, name="reporte_listos_para_liberar"),
    path("licencias-por-vencer/", views.licencias_por_vencer_api, name="reporte_licencias_por_vencer"),
    path("ingresos/", views.ingresos_api, name="reporte_ingresos"),
    path("permisos-pendientes/", views.permisos_pendientes_api, name="reporte_permisos_pendientes"),
]
