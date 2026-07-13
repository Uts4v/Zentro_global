"""
loyalty/admin.py
"""

from django.contrib import admin
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
    MembershipQrToken,
    MerchantMembershipCardDesign,
)


@admin.register(CustomerMerchantProfile)
class CustomerMerchantProfileAdmin(admin.ModelAdmin):
    list_display = ["customer", "merchant", "status", "joined_at"]
    list_filter = ["status"]
    search_fields = ["customer__full_name", "merchant__business_name"]


@admin.register(CustomerMerchantWallet)
class CustomerMerchantWalletAdmin(admin.ModelAdmin):
    list_display = [
        "customer",
        "merchant",
        "points_balance",
        "lifetime_points",
        "tier_level",
        "order_count",
        "streak_days",
    ]
    list_filter = ["tier_level"]
    search_fields = ["customer__full_name", "merchant__business_name"]


@admin.register(LoyaltyRules)
class LoyaltyRulesAdmin(admin.ModelAdmin):
    list_display = ["merchant", "points_per_npr", "streak_multiplier", "welcome_bonus", "updated_at"]
    readonly_fields = ["updated_at"]


@admin.register(MerchantPunchCard)
class MerchantPunchCardAdmin(admin.ModelAdmin):
    list_display = ["name", "merchant", "mode", "stamps_required", "is_active", "created_at"]
    list_filter = ["mode", "is_active"]
    search_fields = ["name", "merchant__business_name"]


@admin.register(CustomerPunchCard)
class CustomerPunchCardAdmin(admin.ModelAdmin):
    list_display = ["customer", "punch_card", "current_stamps", "is_completed", "is_redeemed"]
    list_filter = ["is_completed", "is_redeemed"]
    search_fields = ["customer__full_name", "punch_card__name"]


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ["transaction_type", "customer", "merchant", "points", "status", "created_at"]
    list_filter = ["transaction_type", "status"]
    search_fields = ["customer__full_name", "merchant__business_name"]


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ["title", "required_merchant", "mission_type", "target_count", "reward_points", "is_active"]
    list_filter = ["is_active", "mission_type"]
    search_fields = ["title", "required_merchant__store_name"]
    list_editable = ["is_active"]


@admin.register(CustomerMission)
class CustomerMissionAdmin(admin.ModelAdmin):
    list_display = ["customer", "mission", "current_count", "is_completed", "completed_at"]
    list_filter = ["is_completed"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ["name", "merchant", "points_cost", "stock", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "merchant__store_name"]
    list_editable = ["is_active"]


@admin.register(Redemption)
class RedemptionAdmin(admin.ModelAdmin):
    list_display = ["code", "customer", "reward", "points_spent", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["code", "customer__full_name", "reward__name"]
    readonly_fields = ["created_at"]


@admin.register(MembershipQrToken)
class MembershipQrTokenAdmin(admin.ModelAdmin):
    list_display = ["public_token", "membership", "token_version", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["public_token", "membership__membership_number"]
    readonly_fields = ["public_token", "created_at", "rotated_at"]


@admin.register(MerchantMembershipCardDesign)
class MerchantMembershipCardDesignAdmin(admin.ModelAdmin):
    list_display = [
        "merchant", "card_title", "primary_color", "accent_color",
        "is_published", "updated_at",
    ]
    list_filter = ["is_published", "text_mode", "background_type"]
    search_fields = ["merchant__business_name"]
