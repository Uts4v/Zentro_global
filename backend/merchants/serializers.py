from rest_framework import serializers
from .models import MerchantProfile, MenuItem
import re


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
            "id", "business_name", "slug", "business_type",
            "address", "phone", "logo_url", "banner_url",
            "description", "is_approved", "is_open",
            "onboarding_complete",
            "latitude", "longitude", "qr_code",
            "menu_items", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_approved", "qr_code", "created_at", "updated_at"]

    def validate_slug(self, value):
        # Lowercase, replace spaces with hyphens, strip bad chars
        value = value.lower().strip()
        value = re.sub(r"[^\w-]", "", value.replace(" ", "-"))
        if not value:
            raise serializers.ValidationError("Slug cannot be empty.")
        
        # Uniqueness check — exclude current instance on update
        qs = MerchantProfile.objects.filter(slug=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This slug is already taken.")
        
        return value


class MerchantPublicSerializer(serializers.ModelSerializer):
    """Public merchant data for customer-facing views — no private fields."""

    class Meta:
        model = MerchantProfile
        fields = [
            "id", "business_name", "slug", "business_type",
            "address", "phone", "logo_url", "banner_url",
            "description", "is_open",
            "latitude", "longitude",
        ]