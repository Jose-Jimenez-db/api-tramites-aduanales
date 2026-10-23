from rest_framework.routers import SimpleRouter

from .views import CobroViewSet

router = SimpleRouter()
router.register("cobros", CobroViewSet, basename="cobro")

urlpatterns = router.urls
