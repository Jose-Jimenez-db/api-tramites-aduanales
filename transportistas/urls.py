from django.urls import path

from . import views

urlpatterns = [
    path("", views.transportistas_api, name="transportistas_api"),
    path("<int:id>/", views.transportista_detalle_api, name="transportista_detalle_api"),
]
