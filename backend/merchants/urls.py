# merchants/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MerchantViewSet, MenuItemViewSet

router = DefaultRouter()
router.register(r"profiles", MerchantViewSet, basename="merchant")
router.register(r"menu-items", MenuItemViewSet, basename="menuitem")

urlpatterns = [
    path("", include(router.urls)),
]