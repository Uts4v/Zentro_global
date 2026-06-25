# accounts/serializers.py
from rest_framework import serializers
from .models import User, CustomerProfile


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = [
            "id", "full_name", "loyalty_points", "streak_days",
            "total_orders", "tier", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserSerializer(serializers.ModelSerializer):
    customer_profile = CustomerProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "role", "phone",
            "avatar_url", "customer_profile",
        ]
        read_only_fields = ["id"]