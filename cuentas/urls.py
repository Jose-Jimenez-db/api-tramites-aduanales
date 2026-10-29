from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login_api, name="login_api"),
    path("logout/", views.logout_api, name="logout_api"),
    path("perfil/", views.perfil_api, name="perfil_api"),
    path("usuarios/", views.usuarios_api, name="usuarios_api"),
    path("usuarios/<int:id>/", views.usuario_detalle_api, name="usuario_detalle_api"),
]
