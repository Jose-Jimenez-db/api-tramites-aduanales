from rest_framework.routers import SimpleRouter

from .views import CargaViewSet

router = SimpleRouter()
router.register("cargas", CargaViewSet, basename="carga")

urlpatterns = router.urls
