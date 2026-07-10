"""
loyalty/views.py

All loyalty API endpoints — fully self-contained in Django, no Supabase.
"""

import logging
import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from accounts.models import CustomerProfile, User
from merchants.models import MerchantProfile
from notifications.services import send_notification
from notifications.models import Notification
from orders.models import Order

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
)
from .serializers import (
    LoyaltyRulesSerializer,
    MissionSerializer,
    RewardSerializer,
    RedemptionSerializer,
    CustomerMerchantProfileSerializer,
    CustomerMerchantWalletSerializer,
    MerchantPunchCardSerializer,
    CustomerPunchCardSerializer,
    PointTransactionSerializer,
)
from .services import join_merchant, get_or_create_wallet, deduct_wallet_points, transfer_points

from .models import TodaySpecial
from .serializers import TodaySpecialSerializer

logger = logging.getLogger(__name__)


def _notify_safe(**kwargs):
    """Send a notification without ever letting a failure break the calling flow."""
    try:
        send_notification(**kwargs)
    except Exception:
        logger.exception("Failed to send notification (flow continues)")


@api_view(["GET"])
@permission_classes([AllowAny])
def customer_today_special(request, slug):
    """GET /api/loyalty/specials/<slug>/ — public, returns active special for a merchant."""
    try:
        merchant = MerchantProfile.objects.get(slug=slug)
    except MerchantProfile.DoesNotExist:
        return Response({"error": "Merchant not found."}, status=status.HTTP_404_NOT_FOUND)

    special = TodaySpecial.objects.filter(merchant=merchant, is_active=True).first()
    if not special:
        return Response(None)
    return Response(TodaySpecialSerializer(special).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def merchant_specials_list(request):
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    if request.method == "GET":
        specials = TodaySpecial.objects.filter(merchant=merchant)
        return Response(TodaySpecialSerializer(specials, many=True).data)

    serializer = TodaySpecialSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save(merchant=merchant)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def merchant_special_detail(request, pk):
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    try:
        special = TodaySpecial.objects.get(pk=pk, merchant=merchant)
    except TodaySpecial.DoesNotExist:
        return Response({"error": "Special not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(TodaySpecialSerializer(special).data)

    if request.method == "DELETE":
        special.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = TodaySpecialSerializer(special, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response(serializer.data)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_customer_profile(user) -> CustomerProfile:
    try:
        return user.customer_profile
    except CustomerProfile.DoesNotExist:
        if hasattr(user, 'merchant_profile'):
            raise PermissionError(
                "Merchant accounts cannot access customer loyalty endpoints. "
                "Use /api/loyalty/merchant/* endpoints instead."
            )
        raise PermissionError("No customer profile found for this user.")


def get_merchant_profile(user) -> MerchantProfile:
    try:
        return user.merchant_profile
    except MerchantProfile.DoesNotExist:
        raise PermissionError("No merchant profile found for this user.")


def _customer_error(detail: str):
    return Response({"error": detail}, status=status.HTTP_403_FORBIDDEN)


def _merchant_error(detail: str):
    return Response({"error": detail}, status=status.HTTP_403_FORBIDDEN)


# ── Merchant onboarding (customer ↔ merchant link) ────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def merchant_profile_join(request):
    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    merchant_slug = (request.data.get("merchant_slug") or "").strip()
    merchant_id = request.data.get("merchant_id")

    merchant = None
    if merchant_slug:
        try:
            merchant = MerchantProfile.objects.get(slug=merchant_slug)
        except MerchantProfile.DoesNotExist:
            return Response({"error": "Merchant not found."}, status=status.HTTP_404_NOT_FOUND)
    elif merchant_id:
        try:
            merchant = MerchantProfile.objects.get(id=merchant_id)
        except MerchantProfile.DoesNotExist:
            return Response({"error": "Merchant not found."}, status=status.HTTP_404_NOT_FOUND)
    else:
        return Response(
            {"error": "merchant_slug or merchant_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile, wallet, created = join_merchant(customer, merchant)
    return Response(
        {
            "profile": CustomerMerchantProfileSerializer(profile).data,
            "wallet": CustomerMerchantWalletSerializer(wallet).data,
            "created": created,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_profiles_mine(request):
    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    qs = CustomerMerchantProfile.objects.filter(
        customer=customer,
        status=CustomerMerchantProfile.STATUS_ACTIVE,
    ).select_related("merchant")

    merchant_id = request.query_params.get("merchant")
    if merchant_id:
        qs = qs.filter(merchant_id=merchant_id)

    return Response(CustomerMerchantProfileSerializer(qs, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_joined_merchants(request):
    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    profiles = (
        CustomerMerchantProfile.objects
        .filter(customer=customer, status=CustomerMerchantProfile.STATUS_ACTIVE)
        .select_related("merchant")
        .order_by("-joined_at")
    )

    result = []
    for profile in profiles:
        merchant = profile.merchant
        wallet = CustomerMerchantWallet.objects.filter(
            customer=customer, merchant=merchant
        ).first()
        active_rewards_count = Reward.objects.filter(
            merchant=merchant, is_active=True
        ).count()
        pending_orders_count = Order.objects.filter(
            customer=customer,
            merchant=merchant,
        ).exclude(
            status__in=[Order.STATUS_COMPLETED, Order.STATUS_CANCELLED]
        ).count()

        result.append({
            "merchant_id": merchant.id,
            "merchant_slug": merchant.slug,
            "business_name": merchant.business_name,
            "logo_url": merchant.logo_url,
            "is_open": merchant.is_open,
            "points_balance": wallet.points_balance if wallet else 0,
            "tier_level": wallet.tier_level if wallet else CustomerMerchantWallet.TIER_BRONZE,
            "active_rewards_count": active_rewards_count,
            "pending_orders_count": pending_orders_count,
            "joined_at": profile.joined_at,
        })

    return Response(result)


# ── Merchant wallets ──────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wallet_mine(request):
    merchant_id = request.query_params.get("merchant")
    if not merchant_id:
        return Response({"error": "merchant query param is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    try:
        merchant = MerchantProfile.objects.get(id=merchant_id)
    except MerchantProfile.DoesNotExist:
        return Response({"error": "Merchant not found"}, status=status.HTTP_404_NOT_FOUND)

    wallet = get_or_create_wallet(customer, merchant)
    return Response(CustomerMerchantWalletSerializer(wallet).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wallets_list(request):
    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    wallets = (
        CustomerMerchantWallet.objects
        .filter(customer=customer)
        .select_related("merchant")
        .order_by("-updated_at")
    )
    return Response(CustomerMerchantWalletSerializer(wallets, many=True).data)


# ── Loyalty Rules ─────────────────────────────────────────────────────────────

@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def loyalty_rules(request):
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    rules, _ = LoyaltyRules.objects.get_or_create(merchant=merchant)

    if request.method == "GET":
        return Response(LoyaltyRulesSerializer(rules).data)

    serializer = LoyaltyRulesSerializer(rules, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response(serializer.data)


# ── Transactions ──────────────────────────────────────────────────────────────
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_point_transactions(request):
    merchant_id = request.query_params.get("merchant")
    if not merchant_id:
        return Response({"error": "merchant query param required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    transactions = PointTransaction.objects.filter(customer=customer, merchant_id=merchant_id)
    return Response(PointTransactionSerializer(transactions, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_point_transactions(request):
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    transactions = PointTransaction.objects.filter(merchant=merchant)
    return Response(PointTransactionSerializer(transactions, many=True).data)


# ── Punch Cards ───────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_punch_cards(request):
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    cards = MerchantPunchCard.objects.filter(merchant=merchant)
    return Response(MerchantPunchCardSerializer(cards, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def merchant_punch_card_create(request):
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    serializer = MerchantPunchCardSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(merchant=merchant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def merchant_punch_card_detail(request, pk):
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    try:
        card = MerchantPunchCard.objects.get(pk=pk, merchant=merchant)
    except MerchantPunchCard.DoesNotExist:
        return Response({"error": "Punch card not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(MerchantPunchCardSerializer(card).data)

    serializer = MerchantPunchCardSerializer(card, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_punch_cards(request):
    merchant_id = request.query_params.get("merchant")
    if not merchant_id:
        return Response({"error": "merchant query param required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    # Auto-initialize progress for any active merchant punch card templates
    active_templates = MerchantPunchCard.objects.filter(merchant_id=merchant_id, is_active=True)
    for template in active_templates:
        has_active = CustomerPunchCard.objects.filter(
            customer=customer,
            punch_card=template,
            is_completed=False
        ).exists()
        if not has_active:
            has_completed_unredeemed = CustomerPunchCard.objects.filter(
                customer=customer,
                punch_card=template,
                is_completed=True,
                is_redeemed=False
            ).exists()
            if not has_completed_unredeemed:
                CustomerPunchCard.objects.create(
                    customer=customer,
                    punch_card=template,
                    merchant=template.merchant,
                    current_stamps=0,
                    is_completed=False
                )

    cards = CustomerPunchCard.objects.filter(customer=customer, merchant_id=merchant_id, is_completed=False)
    completed = CustomerPunchCard.objects.filter(customer=customer, merchant_id=merchant_id, is_completed=True, is_redeemed=False)

    return Response({
        "active": CustomerPunchCardSerializer(cards, many=True).data,
        "completed": CustomerPunchCardSerializer(completed, many=True).data,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def customer_punch_card_redeem(request, pk):
    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    try:
        card = (
            CustomerPunchCard.objects
            .select_related("punch_card", "merchant")
            .get(pk=pk, customer=customer)
        )
    except CustomerPunchCard.DoesNotExist:
        return Response({"error": "Punch card not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        card.redeem()
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    CustomerPunchCard.objects.get_or_create(
        customer=customer,
        punch_card=card.punch_card,
        merchant=card.merchant,
        is_completed=False,
        defaults={"current_stamps": 0},
    )

    merchant = card.merchant
    customer_name = customer.full_name or request.user.email
    card_name = card.punch_card.name
    transaction.on_commit(lambda: _notify_safe(
        user=merchant.user,
        title="Punch card redeemed",
        message=f"{customer_name} redeemed their reward on '{card_name}'",
        notification_type=Notification.TYPE_PUNCH_CARD,
        merchant_name=merchant.business_name,
        context_url="/merchant/loyalty",
        merchant_id=merchant.id,
    ))

    return Response(CustomerPunchCardSerializer(card).data)


# ── Missions ──────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([AllowAny])
def mission_list(request):
    missions = Mission.objects.filter(is_active=True).select_related("required_merchant")
    merchant_id = request.query_params.get("merchant")
    if merchant_id:
        missions = missions.filter(required_merchant_id=merchant_id)
    return Response(MissionSerializer(missions, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_missions(request):
    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    missions = Mission.objects.filter(is_active=True).select_related("required_merchant")
    merchant_id = request.query_params.get("merchant")
    if merchant_id:
        missions = missions.filter(required_merchant_id=merchant_id)

    progress_map = {
        cm.mission_id: cm
        for cm in CustomerMission.objects.filter(customer=customer, mission__in=missions)
    }

    result = []
    for mission in missions:
        cm = progress_map.get(mission.id)
        result.append({
            "id": cm.id if cm else f"new-{mission.id}",
            "title": mission.title,
            "description": mission.description,
            "icon": mission.icon,
            "target_count": mission.target_count,
            "current_count": cm.current_count if cm else 0,
            "reward_points": mission.reward_points,
            "is_completed": cm.is_completed if cm else False,
            "mission_type": mission.mission_type,
            "merchant_name": mission.required_merchant.business_name if mission.required_merchant else "",
        })

    return Response(result)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_missions(request):
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    missions = Mission.objects.filter(required_merchant=merchant)
    return Response(MissionSerializer(missions, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mission_create(request):
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    serializer = MissionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save(required_merchant=merchant)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def mission_detail(request, pk):
    try:
        mission = Mission.objects.get(pk=pk)
    except Mission.DoesNotExist:
        return Response({"error": "Mission not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(MissionSerializer(mission).data)

    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    if mission.required_merchant != merchant:
        return Response({"error": "You can only edit your own missions."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "DELETE":
        mission.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = MissionSerializer(mission, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response(serializer.data)


# ── Rewards ───────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([AllowAny])
def reward_list(request):
    rewards = Reward.objects.filter(is_active=True).select_related("merchant")
    merchant_id = request.query_params.get("merchant")
    if merchant_id:
        rewards = rewards.filter(merchant_id=merchant_id)
    return Response(RewardSerializer(rewards, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_rewards(request):
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    rewards = Reward.objects.filter(merchant=merchant)
    return Response(RewardSerializer(rewards, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reward_create(request):
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    serializer = RewardSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save(merchant=merchant)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def reward_detail(request, pk):
    try:
        reward = Reward.objects.get(pk=pk)
    except Reward.DoesNotExist:
        return Response({"error": "Reward not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(RewardSerializer(reward).data)

    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    if reward.merchant != merchant:
        return Response({"error": "You can only edit your own rewards."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "DELETE":
        reward.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = RewardSerializer(reward, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_punch_proof(request, pk):
    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    try:
        card = CustomerPunchCard.objects.select_related(
            "punch_card", "merchant"
        ).get(pk=pk, customer=customer)
    except CustomerPunchCard.DoesNotExist:
        return Response({"error": "Punch card not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        code = card.generate_proof_code()
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "proof_code": code,
        "expires_at": card.proof_code_expires_at,
        "reward_text": card.punch_card.reward_text,
        "store_name": card.merchant.business_name,
        "customer_name": customer.full_name or request.user.email,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def confirm_punch_proof(request):
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    code = (request.data.get("proof_code") or "").strip().upper()
    if not code:
        return Response({"error": "proof_code is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        card = CustomerPunchCard.objects.select_related(
            "customer__user", "punch_card", "merchant"
        ).get(
            proof_code=code,
            merchant=merchant,
            is_completed=True,
            proof_code_used=False,
        )
    except CustomerPunchCard.DoesNotExist:
        return Response(
            {"error": "Invalid code or already used."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if card.proof_code_expires_at and timezone.now() > card.proof_code_expires_at:
        return Response({"error": "This code has expired."}, status=status.HTTP_400_BAD_REQUEST)

    card.proof_code_used = True
    card.save(update_fields=["proof_code_used", "updated_at"])
    card.redeem()

    from orders.models import Order, OrderItem
    redemption_order = Order.objects.create(
        customer=card.customer,
        merchant=merchant,
        status=Order.STATUS_PENDING,
        order_type=Order.ORDER_TYPE_PUNCH_REDEMPTION,
        total_amount=0,
        points_earned=0,
        notes=f"Punch card reward: {card.punch_card.reward_text}",
        punch_card_redemption=card,
    )
    OrderItem.objects.create(
        order=redemption_order,
        name=f"🎁 {card.punch_card.reward_text} (Punch Card Reward)",
        price=0,
        quantity=1,
        subtotal=0,
    )

    CustomerPunchCard.objects.get_or_create(
        customer=card.customer,
        punch_card=card.punch_card,
        merchant=merchant,
        is_completed=False,
        defaults={"current_stamps": 0},
    )

    customer_name = card.customer.full_name or card.customer.user.email
    transaction.on_commit(lambda: _notify_safe(
        user=card.customer.user,
        title="Reward confirmed! 🎉",
        message=f"Your '{card.punch_card.reward_text}' has been confirmed at {merchant.business_name}. A new stamp card has started!",
        notification_type=Notification.TYPE_PUNCH_CARD,
        merchant_name=merchant.business_name,
        context_url=f"/customer/merchant/{merchant.slug}",
        merchant_id=merchant.id,
    ))

    return Response({
        "success": True,
        "customer_name": customer_name,
        "reward_text": card.punch_card.reward_text,
        "order_id": redemption_order.id,
        "new_card_started": True,
    })


# ── Redemptions ───────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def redeem_reward(request, pk):
    """
    POST /api/loyalty/rewards/<id>/redeem/
    Customer redeems a reward using their loyalty points. Creates a real
    Order (order_type=reward_redemption) so the merchant sees it in their
    normal order queue and history, plus a Redemption record for the
    points ledger — mirrors the punch-card redemption flow exactly.
    """
    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    try:
        reward = Reward.objects.select_for_update().get(pk=pk, is_active=True)
    except Reward.DoesNotExist:
        return Response({"error": "Reward not found or inactive."}, status=status.HTTP_404_NOT_FOUND)

    if not reward.is_in_stock:
        return Response({"error": "This reward is out of stock."}, status=status.HTTP_400_BAD_REQUEST)

    wallet = get_or_create_wallet(customer, reward.merchant)
    try:
        deduct_wallet_points(
            wallet,
            reward.points_cost,
            transaction_type="REDEEMED",
            description=f"Redeemed reward: {reward.name}",
            reward=reward
        )
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    if reward.stock > 0:
        reward.stock -= 1
        reward.save(update_fields=["stock"])

    code = uuid.uuid4().hex[:6].upper()
    expires_at = timezone.now() + timedelta(minutes=10)

    redemption = Redemption.objects.create(
        customer=customer,
        reward=reward,
        points_spent=reward.points_cost,
        code=code,
        expires_at=expires_at,
        status=Redemption.STATUS_PENDING,
    )

    # Create a real order so the merchant sees this in their normal order
    # queue and history — same pattern as punch-card redemption orders.
    from orders.models import Order, OrderItem
    redemption_order = Order.objects.create(
        customer=customer,
        merchant=reward.merchant,
        status=Order.STATUS_PENDING,
        order_type=Order.ORDER_TYPE_REWARD_REDEMPTION,
        total_amount=0,
        points_earned=0,
        notes=f"Reward redemption: {reward.name} (code {code})",
        reward_redemption=redemption,
    )
    OrderItem.objects.create(
        order=redemption_order,
        name=f"🎁 {reward.name} (Reward Redemption)",
        price=0,
        quantity=1,
        subtotal=0,
    )

    # Notify the merchant that a customer redeemed a reward — deferred with
    # on_commit so it never risks the redemption transaction, same pattern
    # used for order notifications.
    merchant = reward.merchant
    customer_name = customer.full_name or request.user.email
    transaction.on_commit(lambda: _notify_safe(
        user=merchant.user,
        title="Reward redeemed",
        message=f"{customer_name} redeemed '{reward.name}' — code {code}",
        notification_type=Notification.TYPE_REWARD_REDEEMED,
        merchant_name=merchant.business_name,
        context_url="/merchant/orders",
        merchant_id=merchant.id,
        reward_id=reward.id,
        order_id=redemption_order.id,
    ))

    data = RedemptionSerializer(redemption).data
    data["order_id"] = redemption_order.id
    return Response(data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_redemptions(request):
    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    redemptions = Redemption.objects.filter(customer=customer).select_related("reward")
    return Response(RedemptionSerializer(redemptions, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def confirm_redemption(request):
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    code = (request.data.get("code") or "").strip().upper()
    if not code:
        return Response({"error": "code is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        redemption = Redemption.objects.select_related("customer", "reward__merchant").get(
            code=code,
            status=Redemption.STATUS_PENDING,
            reward__merchant=merchant,
        )
    except Redemption.DoesNotExist:
        return Response({"error": "Invalid code or already used."}, status=status.HTTP_404_NOT_FOUND)

    if redemption.expires_at and timezone.now() > redemption.expires_at:
        redemption.status = Redemption.STATUS_EXPIRED
        redemption.save(update_fields=["status"])
        return Response({"error": "This code has expired."}, status=status.HTTP_400_BAD_REQUEST)

    redemption.status = Redemption.STATUS_CONFIRMED
    redemption.confirmed_at = timezone.now()
    redemption.save(update_fields=["status", "confirmed_at"])

    return Response({
        "success": True,
        "customer_name": redemption.customer.full_name or "Customer",
        "reward_name": redemption.reward.name,
        "points_spent": redemption.points_spent,
        "code": redemption.code,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_redemptions(request):
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    redemptions = (
        Redemption.objects
        .filter(reward__merchant=merchant)
        .select_related("customer", "reward")
        .order_by("-created_at")[:50]
    )
    return Response(RedemptionSerializer(redemptions, many=True).data)


# ── Leaderboard ───────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([AllowAny])
def leaderboard(request):
    limit = min(int(request.query_params.get("limit", 10)), 50)
    merchant_id = request.query_params.get("merchant")

    if not merchant_id:
        return Response(
            {"error": "merchant query param is required for leaderboard."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        MerchantProfile.objects.get(id=merchant_id)
    except MerchantProfile.DoesNotExist:
        return Response({"error": "Merchant not found."}, status=status.HTTP_404_NOT_FOUND)

    qs = (
        CustomerMerchantWallet.objects
        .filter(merchant_id=merchant_id, points_balance__gt=0)
        .select_related("customer__user", "merchant")
        .order_by("-points_balance")[:limit]
    )

    result = [
        {
            "rank": i + 1,
            "customer_id": w.customer_id,
            "full_name": w.customer.full_name or w.customer.user.email,
            "loyalty_points": w.points_balance,
            "lifetime_points": w.lifetime_points,
            "tier": w.tier_level,
            "streak_days": w.streak_days,
            "merchant_id": w.merchant_id,
        }
        for i, w in enumerate(qs)
    ]

    return Response(result)


# ── Point Transfers ────────────────────────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def transfer_create(request):
    """
    POST /api/loyalty/transfers/create/

    Transfer points from the authenticated customer's wallet to another customer.

    Body:
      receiver_customer_id (int)  — recipient CustomerProfile id
      merchant_id (int)           — merchant whose wallet is used
      amount (int)                — points to transfer
      description (str, optional)

    Validation:
      - Sender and receiver must both have wallets at the same merchant.
      - Cross-merchant transfers are BLOCKED.
      - Sender must have sufficient balance.
    """
    try:
        sender_customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    receiver_transfer_code = (request.data.get("receiver_transfer_code") or "").strip().upper()
    merchant_id = request.data.get("merchant_id")
    amount = request.data.get("amount")
    description = (request.data.get("description") or "").strip()

    if not all([receiver_transfer_code, merchant_id, amount]):
        return Response(
            {"error": "receiver_transfer_code, merchant_id, and amount are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return Response({"error": "amount must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

    if amount <= 0:
        return Response({"error": "amount must be positive."}, status=status.HTTP_400_BAD_REQUEST)

    # Resolve merchant
    try:
        merchant = MerchantProfile.objects.get(id=merchant_id)
    except MerchantProfile.DoesNotExist:
        return Response({"error": "Merchant not found."}, status=status.HTTP_404_NOT_FOUND)

    # Resolve receiver by transfer_code
    try:
        receiver_customer = CustomerProfile.objects.get(transfer_code=receiver_transfer_code)
    except CustomerProfile.DoesNotExist:
        return Response({"error": "Receiver not found. Check the transfer code."}, status=status.HTTP_404_NOT_FOUND)

    # Security: verify receiver has joined this merchant
    from .models import CustomerMerchantProfile
    if not CustomerMerchantProfile.objects.filter(
        customer=receiver_customer,
        merchant=merchant,
        status=CustomerMerchantProfile.STATUS_ACTIVE,
    ).exists():
        return Response(
            {"error": "Receiver has not joined this merchant. They must visit the store first."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get sender wallet
    sender_wallet = get_or_create_wallet(sender_customer, merchant)

    # Get or create receiver wallet
    receiver_wallet = get_or_create_wallet(receiver_customer, merchant)

    try:
        result = transfer_points(
            sender_wallet=sender_wallet,
            receiver_wallet=receiver_wallet,
            points=amount,
            description=description,
        )
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Notify receiver
    sender_name = sender_customer.full_name or request.user.email
    receiver_user = receiver_customer.user
    transaction.on_commit(lambda: _notify_safe(
        user=receiver_user,
        title="Points received",
        message=f"{sender_name} sent you {amount} points at {merchant.business_name}.",
        notification_type=Notification.TYPE_TRANSFER_RECEIVED,
        merchant_name=merchant.business_name,
        context_url=f"/customer/merchant/{merchant.slug}",
        merchant_id=merchant.id,
    ))

    # Notify sender
    transaction.on_commit(lambda: _notify_safe(
        user=request.user,
        title="Points sent",
        message=f"You sent {amount} points to {receiver_customer.full_name or receiver_customer.user.email} at {merchant.business_name}.",
        notification_type=Notification.TYPE_TRANSFER_SENT,
        merchant_name=merchant.business_name,
        context_url=f"/customer/merchant/{merchant.slug}",
        merchant_id=merchant.id,
    ))

    return Response({
        "transfer_group": str(result["transfer_group"]),
        "sent_transaction": PointTransactionSerializer(result["sent_transaction"]).data,
        "received_transaction": PointTransactionSerializer(result["received_transaction"]).data,
        "sender_balance": sender_wallet.points_balance,
        "receiver_balance": receiver_wallet.points_balance,
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_transfers(request):
    """
    GET /api/loyalty/transfers/

    Returns all TRANSFER_SENT and TRANSFER_RECEIVED transactions
    for the authenticated customer, optionally filtered by merchant.
    """
    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    qs = PointTransaction.objects.filter(
        customer=customer,
        transaction_type__in=["TRANSFER_SENT", "TRANSFER_RECEIVED"],
    ).select_related("merchant").order_by("-created_at")

    merchant_id = request.query_params.get("merchant")
    if merchant_id:
        qs = qs.filter(merchant_id=merchant_id)

    return Response(PointTransactionSerializer(qs, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_transfer_history(request):
    """
    GET /api/loyalty/merchant/transfers/

    Returns all transfer transactions for the merchant's store.
    """
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    qs = PointTransaction.objects.filter(
        merchant=merchant,
        transaction_type__in=["TRANSFER_SENT", "TRANSFER_RECEIVED"],
    ).select_related("customer__user").order_by("-created_at")

    return Response(PointTransactionSerializer(qs, many=True).data)