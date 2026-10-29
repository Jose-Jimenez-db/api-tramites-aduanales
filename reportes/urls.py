from django.urls import path

from . import views

urlpatterns = [
    path("resumen-clientes/", views.resumen_clientes_api, name="reporte_resumen_clientes"),
    path("tramites-por-estado/", views.tramites_por_estado_api, name="reporte_tramites_por_estado"),
    path("listos-para-liberar/", views.listos_para_liberar_api, name="reporte_listos_para_liberar"),
    path("licencias-por-vencer/", views.licencias_por_vencer_api, name="reporte_licencias_por_vencer"),
    path("ingresos/", views.ingresos_api, name="reporte_ingresos"),
    path("permisos-pendientes/", views.permisos_pendientes_api, name="reporte_permisos_pendientes"),
]
