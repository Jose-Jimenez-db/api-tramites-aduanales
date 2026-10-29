from django.urls import path

from . import views

# Qué hace: Se definen las rutas de cargas (van bajo /api/cargas/).
# Qué usa: path() de Django y las vistas de views.py.
# Cómo lo hace: Cada path une una dirección con la vista que la atiende. <int:id> toma el número de
#     la URL y se lo pasa a la vista como id. Así se hacen las rutas a mano, sin routers, como
#     pidió el profesor.
urlpatterns = [
    path("", views.cargas_api, name="cargas_api"),
    path("<int:id>/", views.carga_detalle_api, name="carga_detalle_api"),
]
