# merchants/admin.py
from django.contrib import admin
from .models import MerchantProfile, MenuItem


@admin.register(MerchantProfile)
class MerchantProfileAdmin(admin.ModelAdmin):
    list_display = [
        "business_name",   # was store_name
        "slug",            # was store_slug
        "phone",
        "is_approved",
        "is_open",
        "onboarding_complete",
        "created_at",
    ]
    list_filter = ["is_approved", "is_open", "onboarding_complete"]
    search_fields = ["business_name", "slug", "phone", "address"]
    prepopulated_fields = {"slug": ("business_name",)}  # was store_slug / store_name
    readonly_fields = ["qr_code", "created_at", "updated_at"]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "merchant",
        "category",
        "price",
        "is_available",
        "is_featured",
        "points_per_item",
    ]
    list_filter = ["is_available", "is_featured", "category"]
    search_fields = ["name", "merchant__business_name"]  # was merchant__store_name