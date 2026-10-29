from django.urls import path

from . import views

# Qué hace: Se definen las rutas de login, logout, perfil y usuarios (van bajo /api/auth/).
# Qué usa: path() de Django y las vistas de views.py.
# Cómo lo hace: Cada path une una dirección con la vista que la atiende. <int:id> toma el número de
#     la URL y se lo pasa a la vista como id. Así se hacen las rutas a mano, sin routers, como
#     pidió el profesor.
urlpatterns = [
    path("login/", views.login_api, name="login_api"),
    path("logout/", views.logout_api, name="logout_api"),
    path("perfil/", views.perfil_api, name="perfil_api"),
    path("usuarios/", views.usuarios_api, name="usuarios_api"),
    path("usuarios/<int:id>/", views.usuario_detalle_api, name="usuario_detalle_api"),
]
