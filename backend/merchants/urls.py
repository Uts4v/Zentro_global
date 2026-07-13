# merchants/urls.py
"""
Mounted at /api/merchants/

Order matters — specific paths (me/, analytics/, menu-items/, slug/)
must come before the generic <int:pk>/ catch-all.
"""

from django.urls import path
from . import views

urlpatterns = [
    # ── Authenticated merchant ────────────────────────────────────────────────
    path("me/",                  views.merchant_me,             name="merchant-me"),
    path("me/update/",           views.merchant_update,         name="merchant-update"),
    path("me/regenerate-qr/",    views.merchant_regenerate_qr,  name="merchant-regenerate-qr"),
    path("analytics/",           views.merchant_analytics,      name="merchant-analytics"),
# ── Public merchant pages ─────────────────────────────────────────────────
    path("",                     views.merchant_list,           name="merchant-list"),
    path("nearby/",               views.merchant_discovery_nearby, name="merchant-nearby"),
    path("slug/<slug:slug>/",    views.merchant_by_slug,        name="merchant-by-slug"),
    path("<int:pk>/",            views.merchant_detail,         name="merchant-detail"),
    path("<int:pk>/menu/",       views.merchant_menu,           name="merchant-public-menu"),
    # ── Menu items ────────────────────────────────────────────────────────────
    path("menu-items/my-items/", views.my_menu_items,           name="my-menu-items"),
    path("menu-items/",          views.menu_item_list_create,   name="menu-item-list-create"),
    path("menu-items/<int:pk>/", views.menu_item_detail,        name="menu-item-detail"),
    path(
        "menu-items/<int:pk>/toggle-availability/",
        views.toggle_availability,
        name="toggle-availability",
    ),

    # ── Table management ──────────────────────────────────────────────────────
    path("tables/",                          views.merchant_tables,            name="merchant-tables"),
    path("tables/generate/",                 views.merchant_tables_generate,   name="merchant-tables-generate"),
    path("tables/<int:pk>/",                 views.merchant_table_detail,      name="merchant-table-detail"),
    path("tables/<int:pk>/delete/",          views.merchant_table_delete,      name="merchant-table-delete"),
    path("tables/<int:pk>/regenerate-qr/",   views.merchant_table_regenerate_qr, name="merchant-table-regenerate-qr"),

    # ── Public table resolution ───────────────────────────────────────────────
    path("public/<slug:slug>/tables/<str:public_token>/", views.public_resolve_table, name="public-resolve-table"),

    # ── Public merchant pages ─────────────────────────────────────────────────
    path("",                     views.merchant_list,           name="merchant-list"),
    path("slug/<slug:slug>/",    views.merchant_by_slug,        name="merchant-by-slug"),
    path("<int:pk>/",            views.merchant_detail,         name="merchant-detail"),
    path("<int:pk>/menu/",       views.merchant_menu,           name="merchant-public-menu"),
]