"""
loyalty/customer_urls.py — mounted at /api/customer/memberships/

Wires up the membership endpoints that were defined in views.py
but never registered anywhere.
"""

from django.urls import path
from . import views

urlpatterns = [
    path("", views.membership_list, name="membership-list"),
    path("join/", views.membership_join, name="membership-join"),
    path("<slug:merchant_slug>/qr/", views.membership_qr, name="membership-qr"),
    path("<slug:merchant_slug>/", views.membership_detail_by_slug, name="membership-detail-by-slug"),
]