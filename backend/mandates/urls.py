from rest_framework.routers import DefaultRouter

from .views import PropertyMandateViewSet


router = DefaultRouter()
router.register(
    "mandates",
    PropertyMandateViewSet,
    basename="mandate",
)

urlpatterns = router.urls
