from django.urls import path

from . import views

# Qué hace: Se definen las rutas de clientes (van bajo /api/clientes/).
# Qué usa: path() de Django y las vistas de views.py.
# Cómo lo hace: Cada path une una dirección con la vista que la atiende. <int:id> toma el número de
#     la URL y se lo pasa a la vista como id. Así se hacen las rutas a mano, sin routers, como
#     pidió el profesor.
urlpatterns = [
    path("", views.clientes_api, name="clientes_api"),
    path("<int:id>/", views.cliente_detalle_api, name="cliente_detalle_api"),
]
