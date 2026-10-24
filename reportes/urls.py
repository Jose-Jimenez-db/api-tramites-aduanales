from django.urls import path

from . import views

urlpatterns = [
    path("resumen-clientes/", views.ResumenClientesView.as_view(), name="reporte-resumen-clientes"),
    path("tramites-por-estado/", views.TramitesPorEstadoView.as_view(), name="reporte-tramites-estado"),
    path("listos-para-liberar/", views.ListosParaLiberarView.as_view(), name="reporte-listos-liberar"),
    path("licencias-por-vencer/", views.LicenciasPorVencerView.as_view(), name="reporte-licencias"),
    path("ingresos/", views.IngresosView.as_view(), name="reporte-ingresos"),
    path("permisos-pendientes/", views.PermisosPendientesView.as_view(), name="reporte-permisos"),
]
