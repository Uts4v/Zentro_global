"""
loyalty/services.py

Merchant-scoped loyalty helpers — wallets, onboarding, point operations.
"""

from django.utils import timezone

from .models import CustomerMerchantProfile, CustomerMerchantWallet, PointTransaction


def get_or_create_wallet(customer, merchant) -> CustomerMerchantWallet:
    wallet, _ = CustomerMerchantWallet.objects.get_or_create(
        customer=customer,
        merchant=merchant,
        defaults={"tier_level": CustomerMerchantWallet.TIER_BRONZE},
    )
    return wallet


def join_merchant(customer, merchant):
    """
    Link a customer to a merchant. Creates profile + wallet if missing.
    Returns (profile, wallet, profile_created).
    """
    profile, profile_created = CustomerMerchantProfile.objects.get_or_create(
        customer=customer,
        merchant=merchant,
        defaults={"status": CustomerMerchantProfile.STATUS_ACTIVE},
    )
    if profile.status != CustomerMerchantProfile.STATUS_ACTIVE:
        profile.status = CustomerMerchantProfile.STATUS_ACTIVE
        profile.save(update_fields=["status", "updated_at"])

    wallet = get_or_create_wallet(customer, merchant)
    return profile, wallet, profile_created


def recalculate_tier(wallet: CustomerMerchantWallet):
    pts = wallet.lifetime_points
    if pts >= 5000:
        tier = CustomerMerchantWallet.TIER_PLATINUM
    elif pts >= 2000:
        tier = CustomerMerchantWallet.TIER_GOLD
    elif pts >= 500:
        tier = CustomerMerchantWallet.TIER_SILVER
    else:
        tier = CustomerMerchantWallet.TIER_BRONZE

    if wallet.tier_level != tier:
        wallet.tier_level = tier
        wallet.save(update_fields=["tier_level", "updated_at"])


def award_wallet_points(wallet: CustomerMerchantWallet, pts: int, transaction_type="EARNED", description="", order=None, reward=None, mission=None, punch_card=None):
    if pts <= 0:
        return
        
    balance_before = wallet.points_balance
    wallet.points_balance = max(0, wallet.points_balance + pts)
    wallet.lifetime_points += pts
    wallet.last_point_earned_at = timezone.now()
    wallet.save(
        update_fields=[
            "points_balance",
            "lifetime_points",
            "last_point_earned_at",
            "updated_at",
        ]
    )
    recalculate_tier(wallet)
    
    PointTransaction.objects.create(
        merchant=wallet.merchant,
        customer=wallet.customer,
        wallet=wallet,
        transaction_type=transaction_type,
        points=pts,
        balance_before=balance_before,
        balance_after=wallet.points_balance,
        description=description,
        order=order,
        reward=reward,
        mission=mission,
        punch_card=punch_card
    )


def deduct_wallet_points(wallet: CustomerMerchantWallet, pts: int, transaction_type="REDEEMED", description="", order=None, reward=None, mission=None, punch_card=None):
    if wallet.points_balance < pts:
        raise ValueError(
            f"Insufficient points: have {wallet.points_balance}, need {pts}"
        )
        
    balance_before = wallet.points_balance
    wallet.points_balance -= pts
    wallet.save(update_fields=["points_balance", "updated_at"])
    
    PointTransaction.objects.create(
        merchant=wallet.merchant,
        customer=wallet.customer,
        wallet=wallet,
        transaction_type=transaction_type,
        points=-pts,
        balance_before=balance_before,
        balance_after=wallet.points_balance,
        description=description,
        order=order,
        reward=reward,
        mission=mission,
        punch_card=punch_card
    )


def update_wallet_streak(wallet: CustomerMerchantWallet, now=None) -> bool:
    """
    Update merchant-scoped streak based on order datetime.
    Requires a 12-hour gap between orders to increment the streak.
    Returns True if the streak was successfully incremented, False otherwise.
    """
    now = now or timezone.now()
    last = wallet.last_order_datetime
    incremented = False

    if last is None:
        wallet.streak_days = 1
        incremented = True
    else:
        time_diff = now - last
        hours_diff = time_diff.total_seconds() / 3600.0

        if hours_diff >= 12 and hours_diff <= 36:
            # Between 12 and 36 hours is considered the next "day/streak period"
            wallet.streak_days += 1
            incremented = True
        elif hours_diff > 36:
            # Streak broken
            wallet.streak_days = 1
            incremented = True
        else:
            # Too soon (under 12 hours) - don't increment, don't update last_order_datetime for streak purposes
            # We still want to return False, but we shouldn't necessarily skip updating the datetime.
            # Actually, to prevent abuse where someone orders every 11 hours and never gets a streak,
            # we should update the datetime if we increment or if it's the first time.
            # Wait, if we don't increment, we shouldn't update last_order_datetime, otherwise they might keep resetting their 12 hour window?
            # Actually, if we just keep last_order_datetime as the time of the *last successful streak increment*, it works perfectly.
            return False

    wallet.last_order_datetime = now
    wallet.save(update_fields=["streak_days", "last_order_datetime", "updated_at"])
    return incremented
