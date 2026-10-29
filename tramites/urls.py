from django.urls import path

from . import views

# Qué hace: Se definen las rutas de trámites y sus acciones cambiar-estado y resolver-permiso (van
#     bajo /api/tramites/).
# Qué usa: path() de Django y las vistas de views.py.
# Cómo lo hace: Cada path une una dirección con la vista que la atiende. <int:id> toma el número de
#     la URL y se lo pasa a la vista como id. Así se hacen las rutas a mano, sin routers, como
#     pidió el profesor.
urlpatterns = [
    path("", views.tramites_api, name="tramites_api"),
    path("<int:id>/", views.tramite_detalle_api, name="tramite_detalle_api"),
    path("<int:id>/cambiar-estado/", views.tramite_cambiar_estado_api, name="tramite_cambiar_estado_api"),
    path("<int:id>/resolver-permiso/", views.tramite_resolver_permiso_api, name="tramite_resolver_permiso_api"),
]
