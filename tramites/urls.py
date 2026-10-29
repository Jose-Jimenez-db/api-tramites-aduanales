from django.urls import path

from . import views

urlpatterns = [
    path("", views.tramites_api, name="tramites_api"),
    path("<int:id>/", views.tramite_detalle_api, name="tramite_detalle_api"),
    path("<int:id>/cambiar-estado/", views.tramite_cambiar_estado_api, name="tramite_cambiar_estado_api"),
    path("<int:id>/resolver-permiso/", views.tramite_resolver_permiso_api, name="tramite_resolver_permiso_api"),
]
