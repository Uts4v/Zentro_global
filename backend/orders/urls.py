"""
orders/urls.py — mounted at /api/orders/
"""

from django.urls import path
from . import views

urlpatterns = [
    path("my-orders/", views.my_orders, name="my-orders"),
    path("store-orders/", views.store_orders, name="store-orders"),
    path("create/", views.create_order, name="create-order"),
    path("guest-create/", views.guest_create_order, name="guest-create-order"),
    path("merchant-history/", views.merchant_order_history, name="merchant-order-history"),
    path("<int:pk>/", views.order_detail, name="order-detail"),
    path("<int:pk>/update-status/", views.update_order_status, name="update-order-status"),
    path("<int:pk>/cancel/", views.cancel_order, name="cancel-order"),
]
