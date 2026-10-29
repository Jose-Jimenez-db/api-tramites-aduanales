from django.urls import path

from . import views

urlpatterns = [
    path("", views.cobros_api, name="cobros_api"),
    path("<int:id>/", views.cobro_detalle_api, name="cobro_detalle_api"),
    path("<int:id>/registrar-pago/", views.cobro_registrar_pago_api, name="cobro_registrar_pago_api"),
    path("<int:id>/anular/", views.cobro_anular_api, name="cobro_anular_api"),
]
