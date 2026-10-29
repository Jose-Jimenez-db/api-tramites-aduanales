from django.urls import path

from . import views

urlpatterns = [
    path("", views.clientes_api, name="clientes_api"),
    path("<int:id>/", views.cliente_detalle_api, name="cliente_detalle_api"),
]
