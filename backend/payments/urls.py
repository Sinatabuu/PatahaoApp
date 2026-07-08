from rest_framework.routers import DefaultRouter
from .views import DealViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r"deals", DealViewSet, basename="deal")
router.register(r"payments", PaymentViewSet, basename="payment")

urlpatterns = router.urls
