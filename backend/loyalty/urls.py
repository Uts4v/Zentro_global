# loyalty/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MissionViewSet,
    CustomerMissionViewSet,
    RewardViewSet,
    RedemptionViewSet,
    PunchCardViewSet,
    MerchantPunchCardViewSet,
)

router = DefaultRouter()
router.register(r"missions", MissionViewSet, basename="mission")
router.register(r"customer-missions", CustomerMissionViewSet, basename="customer-mission")
router.register(r"rewards", RewardViewSet, basename="reward")
router.register(r"redemptions", RedemptionViewSet, basename="redemption")
router.register(r"punch-cards", PunchCardViewSet, basename="punch-card")
router.register(r"merchant-punch-cards", MerchantPunchCardViewSet, basename="merchant-punch-card")

urlpatterns = [
    path("", include(router.urls)),
]