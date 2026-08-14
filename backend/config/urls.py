from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.http import JsonResponse
from django.urls import include, path

def home(request):
    return JsonResponse(
        {
            "name": "Pata Hao API",
            "status": "running",
            "message": "Backend server is working.",
            "endpoints": {
                "admin": "/admin/",
                "api": "/api/",
                "login": "/api/auth/login/",
                "refresh": "/api/auth/refresh/",
            },
        }
    )

urlpatterns = [
     
    path("", home, name="home"),
    path("admin/", admin.site.urls),

    # Auth
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # App APIs
    path("api/", include("properties.urls")),
    path("api/", include("properties.favorite_urls")),
    path("api/", include("partners.urls")),
    path("api/", include("accounts.urls")),
    path("api/", include("viewings.urls")),
    path("api/", include("payments.urls")),
    path("api/", include("notifications.urls")),
    path("api/", include("core.urls")),
    path("api/", include("deals.urls")),
    path("api/", include("commissions.urls")),
    path("api/", include("governance.urls")),
    path("api/", include("mandates.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


