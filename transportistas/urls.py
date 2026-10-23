from rest_framework.routers import SimpleRouter

from .views import TransportistaViewSet

router = SimpleRouter()
router.register("transportistas", TransportistaViewSet, basename="transportista")

urlpatterns = router.urls
