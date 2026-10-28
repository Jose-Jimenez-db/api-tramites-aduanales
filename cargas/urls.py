from django.urls import path

from . import views

urlpatterns = [
    path("", views.cargas_api, name="cargas_api"),
    path("<int:id>/", views.carga_detalle_api, name="carga_detalle_api"),
]
