from django.urls import path

from . import views

# Qué hace: Se definen las rutas de cobros y sus acciones registrar-pago y anular (van bajo
#     /api/cobros/).
# Qué usa: path() de Django y las vistas de views.py.
# Cómo lo hace: Cada path une una dirección con la vista que la atiende. <int:id> toma el número de
#     la URL y se lo pasa a la vista como id. Así se hacen las rutas a mano, sin routers, como
#     pidió el profesor.
urlpatterns = [
    path("", views.cobros_api, name="cobros_api"),
    path("<int:id>/", views.cobro_detalle_api, name="cobro_detalle_api"),
    path("<int:id>/registrar-pago/", views.cobro_registrar_pago_api, name="cobro_registrar_pago_api"),
    path("<int:id>/anular/", views.cobro_anular_api, name="cobro_anular_api"),
]
