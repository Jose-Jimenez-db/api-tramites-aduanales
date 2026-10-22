from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import LoginView, LogoutView, PerfilView, UsuarioViewSet

router = SimpleRouter()
router.register("usuarios", UsuarioViewSet, basename="usuario")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("perfil/", PerfilView.as_view(), name="perfil"),
] + router.urls
