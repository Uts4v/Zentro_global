from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/accounts/", include("accounts.urls")),
    path("api/merchants/", include("merchants.urls")),
    path("api/loyalty/", include("loyalty.urls")),
    path("api/orders/", include("orders.urls")),
]