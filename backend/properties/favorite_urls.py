from rest_framework.routers import DefaultRouter

from .favorite_views import PropertyFavoriteViewSet


router = DefaultRouter()

router.register(
    r"favorites",
    PropertyFavoriteViewSet,
    basename="favorite",
)

urlpatterns = router.urls
