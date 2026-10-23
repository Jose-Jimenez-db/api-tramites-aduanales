from rest_framework.routers import SimpleRouter

from .views import TipoPermisoViewSet, TramiteViewSet

router = SimpleRouter()
router.register("tipos-permiso", TipoPermisoViewSet, basename="tipo-permiso")
router.register("tramites", TramiteViewSet, basename="tramite")

urlpatterns = router.urls
