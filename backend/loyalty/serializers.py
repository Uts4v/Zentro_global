"""
loyalty/serializers.py
"""

from rest_framework import serializers
from .models import (
    LoyaltyRules,
    Mission,
    CustomerMission,
    Reward,
    Redemption,
    CustomerMerchantProfile,
    CustomerMerchantWallet,
    MerchantPunchCard,
    CustomerPunchCard,
    PointTransaction,
    TodaySpecial,
)

class LoyaltyRulesSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyRules
        fields = [
            "id",
            "points_per_npr",
            "streak_multiplier",
            "welcome_bonus",
            "birthday_bonus",
            "streak_min_amount",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class MerchantPunchCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = MerchantPunchCard
        fields = [
            "id",
            "merchant",
            "name",
            "mode",
            "stamps_required",
            "reward_text",
            "background_image",
            "animated_gif_background",
            "color_scheme",
            "stamp_icon",
            "logo",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "merchant", "created_at", "updated_at"]


class CustomerPunchCardSerializer(serializers.ModelSerializer):
    punch_card = MerchantPunchCardSerializer(read_only=True)
    merchant_name = serializers.CharField(source="merchant.business_name", read_only=True)

    class Meta:
        model = CustomerPunchCard
        fields = [
            "id",
            "customer",
            "punch_card",
            "merchant",
            "merchant_name",
            "current_stamps",
            "is_completed",
            "completed_at",
            "is_redeemed",
            "redeemed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "customer", "punch_card", "merchant", "merchant_name", "created_at", "updated_at"]

class PointTransactionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    merchant_name = serializers.CharField(source="merchant.business_name", read_only=True)

    class Meta:
        model = PointTransaction
        fields = [
            "id",
            "merchant",
            "merchant_name",
            "customer",
            "customer_name",
            "transaction_type",
            "points",
            "balance_before",
            "balance_after",
            "expiry_date",
            "status",
            "description",
            "created_at",
        ]
        read_only_fields = fields


class MissionSerializer(serializers.ModelSerializer):
    required_merchant_name = serializers.CharField(
        source="required_merchant.business_name",
        read_only=True,
        default="",
    )

    class Meta:
        model = Mission
        fields = [
            "id",
            "title",
            "description",
            "icon",
            "mission_type",
            "target_count",
            "reward_points",
            "required_merchant",
            "required_merchant_name",
            "is_active",
            "starts_at",
            "ends_at",
            "created_at",
        ]
        read_only_fields = ["id", "required_merchant", "required_merchant_name", "created_at"]
class TodaySpecialSerializer(serializers.ModelSerializer):
    linked_menu_item_name = serializers.CharField(
        source="linked_menu_item.name", read_only=True, default=None
    )
    linked_reward_name = serializers.CharField(
        source="linked_reward.name", read_only=True, default=None
    )

    class Meta:
        model = TodaySpecial
        fields = [
            "id", "title", "description", "image_url",
            "linked_menu_item", "linked_menu_item_name",
            "linked_reward", "linked_reward_name",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

class CustomerMissionSerializer(serializers.ModelSerializer):
    """Customer-facing: mission details + customer's progress."""

    mission = MissionSerializer(read_only=True)

    class Meta:
        model = CustomerMission
        fields = [
            "id",
            "mission",
            "current_count",
            "is_completed",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "mission", "created_at", "updated_at"]


class MissionViewSerializer(serializers.Serializer):
    """
    Flat view used by the /my-missions/ endpoint.
    Mirrors the Supabase MissionView interface.
    """

    id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    icon = serializers.CharField()
    target_count = serializers.IntegerField()
    current_count = serializers.IntegerField()
    reward_points = serializers.IntegerField()
    is_completed = serializers.BooleanField()
    mission_type = serializers.CharField()
    merchant_name = serializers.CharField(default="")


class RewardSerializer(serializers.ModelSerializer):
    merchant_name = serializers.CharField(source="merchant.business_name", read_only=True)

    class Meta:
        model = Reward
        fields = [
            "id",
            "merchant",
            "merchant_name",
            "name",
            "description",
            "emoji",
            "points_cost",
            "image_url",
            "is_active",
            "stock",
            "created_at",
        ]
        read_only_fields = ["id", "merchant", "merchant_name", "created_at"]


class RedemptionSerializer(serializers.ModelSerializer):
    reward = RewardSerializer(read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)

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
            "confirmed_at",
            "expires_at",
            "created_at",
        ]
        read_only_fields = ["id", "customer", "customer_name", "reward", "created_at"]


class CustomerMerchantProfileSerializer(serializers.ModelSerializer):
    merchant_id = serializers.IntegerField(source="merchant.id", read_only=True)
    merchant_name = serializers.CharField(source="merchant.business_name", read_only=True)
    merchant_slug = serializers.CharField(source="merchant.slug", read_only=True)

    class Meta:
        model = CustomerMerchantProfile
        fields = [
            "id",
            "merchant_id",
            "merchant_name",
            "merchant_slug",
            "joined_at",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CustomerMerchantWalletSerializer(serializers.ModelSerializer):
    merchant_id = serializers.IntegerField(source="merchant.id", read_only=True)
    merchant_name = serializers.CharField(source="merchant.business_name", read_only=True)
    merchant_slug = serializers.CharField(source="merchant.slug", read_only=True)

    class Meta:
        model = CustomerMerchantWallet
        fields = [
            "id",
            "merchant_id",
            "merchant_name",
            "merchant_slug",
            "points_balance",
            "lifetime_points",
            "expired_points",
            "order_count",
            "streak_days",
            "last_order_datetime",
            "last_point_earned_at",
            "tier_level",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
