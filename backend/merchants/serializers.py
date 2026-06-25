# merchants/serializers.py
from rest_framework import serializers
from .models import MerchantProfile, MenuItem


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = [
            "id", "name", "description", "price", "image_url",
            "category", "is_available", "is_featured", "loyalty_reward",
            "points_per_item", "emoji",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MerchantProfileSerializer(serializers.ModelSerializer):
    menu_items = MenuItemSerializer(many=True, read_only=True)

    class Meta:
        model = MerchantProfile
        fields = [
            "id", "store_name", "store_slug", "business_type",
            "address", "phone", "logo_url", "banner_url",
            "description", "is_approved", "is_open",
            "menu_items", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MerchantPublicSerializer(serializers.ModelSerializer):
    """Public merchant data for customer-facing views."""

    class Meta:
        model = MerchantProfile
        fields = [
            "id", "store_name", "store_slug", "business_type",
            "address", "logo_url", "banner_url", "description", "is_open",
        ]