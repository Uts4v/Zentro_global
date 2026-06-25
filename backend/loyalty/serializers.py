# loyalty/serializers.py
from rest_framework import serializers
from .models import Mission, CustomerMission, Reward, Redemption, PunchCard


class MissionSerializer(serializers.ModelSerializer):
    required_merchant_name = serializers.CharField(
        source="required_merchant.store_name",
        read_only=True,
    )

    class Meta:
        model = Mission
        fields = [
            "id",
            "title",
            "description",
            "mission_type",
            "points_reward",
            "required_count",
            "required_merchant",
            "required_merchant_name",
            "is_active",
            "starts_at",
            "ends_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "required_merchant",
            "required_merchant_name",
            "created_at",
        ]


class CustomerMissionSerializer(serializers.ModelSerializer):
    mission = MissionSerializer(read_only=True)

    class Meta:
        model = CustomerMission
        fields = [
            "id",
            "mission",
            "progress",
            "is_completed",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "mission",
            "created_at",
            "updated_at",
        ]


class RewardSerializer(serializers.ModelSerializer):
    merchant_name = serializers.CharField(
        source="merchant.store_name",
        read_only=True,
    )

    class Meta:
        model = Reward
        fields = [
            "id",
            "merchant",
            "merchant_name",
            "name",
            "description",
            "points_cost",
            "image_url",
            "is_active",
            "stock",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "merchant",
            "merchant_name",
            "created_at",
        ]


class RedemptionSerializer(serializers.ModelSerializer):
    reward = RewardSerializer(read_only=True)
    customer_name = serializers.CharField(
        source="customer.full_name",
        read_only=True,
    )

    class Meta:
        model = Redemption
        fields = [
            "id",
            "customer",
            "customer_name",
            "reward",
            "points_spent",
            "status",
            "code",
            "redeemed_at",
            "expires_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "customer",
            "customer_name",
            "reward",
            "points_spent",
            "status",
            "code",
            "redeemed_at",
            "expires_at",
            "created_at",
        ]


class PunchCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = PunchCard
        fields = [
            "id",
            "customer",
            "merchant",
            "punch_count",
            "punches_to_free",
            "lifetime_punches",
            "free_reward_available",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "customer",
            "merchant",
            "updated_at",
        ]