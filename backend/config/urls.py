"""
Root URL configuration for Zentro backend.

All API routes are prefixed with /api/.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import upload_image

urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth: register, login, logout, token refresh, password reset, profile
    path("api/auth/", include("accounts.urls")),
    path("api/notifications/", include("notifications.urls")),
    # Media upload (images)
    path("api/media/upload/", upload_image, name="media-upload"),

    # Merchants + menu items
    path("api/merchants/", include("merchants.urls")),

    # Loyalty: missions, rewards, redemptions, punch cards, rules
    path("api/loyalty/", include("loyalty.urls")),

    # Orders
    path("api/orders/", include("orders.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
