"""
loyalty/memberships_urls.py — mounted at /api/customer/memberships/

Separate URL file so the membership endpoints live at the /api/customer/
prefix as specified, while the rest of the loyalty app stays under
/api/loyalty/.
"""

from django.urls import path
from . import views

urlpatterns = [
    path("", views.membership_list, name="membership-list"),
    path("join/", views.membership_join, name="membership-join"),
    path("<slug:merchant_slug>/", views.membership_detail_by_slug, name="membership-detail-by-slug"),
    path("<slug:merchant_slug>/qr/", views.membership_qr, name="membership-qr"),
]
