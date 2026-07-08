from rest_framework.routers import DefaultRouter
from .views import ViewingViewSet

router = DefaultRouter()
router.register(r"viewings", ViewingViewSet, basename="viewing")

urlpatterns = router.urls
