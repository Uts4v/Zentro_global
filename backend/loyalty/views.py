"""
loyalty/views.py

All loyalty API endpoints — fully self-contained in Django, no Supabase.

Endpoints:
  GET/POST   /api/loyalty/rules/               — merchant CRUD for loyalty rules
  GET        /api/loyalty/punch-cards/mine/    — customer's punch card for a merchant
  POST       /api/loyalty/punch-cards/use-free-reward/
  GET        /api/loyalty/missions/            — active missions list
  GET        /api/loyalty/missions/my-missions/— customer progress view
  GET/POST   /api/loyalty/missions/merchant/   — merchant CRUD
  PATCH/DELETE /api/loyalty/missions/<id>/
  GET        /api/loyalty/rewards/             — active rewards list (customer)
  GET/POST   /api/loyalty/rewards/merchant/    — merchant CRUD
  PATCH/DELETE /api/loyalty/rewards/<id>/
  POST       /api/loyalty/rewards/<id>/redeem/ — customer redeems a reward
  GET        /api/loyalty/redemptions/         — customer's own redemptions
  POST       /api/loyalty/redemptions/confirm/ — merchant confirms a redemption code
  GET        /api/loyalty/leaderboard/         — top customers by points
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
from .services import join_merchant, get_or_create_wallet, deduct_wallet_points

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
    """
    GET /api/loyalty/specials/<slug>/
    Public — returns the single active special for a merchant slug.
    """
    try:
        merchant = MerchantProfile.objects.get(slug=slug)
    except MerchantProfile.DoesNotExist:
        return Response({"error": "Merchant not found."}, status=status.HTTP_404_NOT_FOUND)

    special = (
        TodaySpecial.objects
        .filter(merchant=merchant, is_active=True)
        .first()
    )
    if not special:
        return Response(None)
    return Response(TodaySpecialSerializer(special).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def merchant_specials_list(request):
    """
    GET  /api/loyalty/merchant/specials/  — list all specials
    POST /api/loyalty/merchant/specials/  — create a special
    """
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
    """
    GET    /api/loyalty/merchant/specials/<pk>/
    PATCH  /api/loyalty/merchant/specials/<pk>/
    DELETE /api/loyalty/merchant/specials/<pk>/
    """
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
        # Check if they're a merchant — give a helpful error
        if hasattr(user, 'merchant_profile'):
            raise PermissionError(
                "Merchant accounts cannot access customer loyalty endpoints. "
                "Use /api/loyalty/merchant/* endpoints instead."
            )
        raise PermissionError("No customer profile found for this user.")

def get_merchant_profile(user) -> MerchantProfile:
    """Return the merchant profile or raise a descriptive error."""
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
    """
    POST /api/loyalty/merchant-profiles/join/
    Body: { "merchant_slug": "cafe-a" } OR { "merchant_id": 1 }

    Creates CustomerMerchantProfile + CustomerMerchantWallet.
    Backend verifies the merchant exists — never trust slug from frontend alone.
    """
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
    """
    GET /api/loyalty/merchant-profiles/mine/
    ?merchant=<id> — optional filter for a single merchant profile
    """
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


# ── Merchant wallets ──────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wallet_mine(request):
    """
    GET /api/loyalty/wallets/mine/?merchant=<id>
    Returns the customer's wallet for the given merchant.
    """
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
    """GET /api/loyalty/wallets/ — all merchant wallets for the logged-in customer."""
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
    """
    GET   — merchant fetches their rules (returns defaults if none exist yet)
    PUT/PATCH — merchant saves rules
    """
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
    """GET /api/loyalty/transactions/?merchant=<id>"""
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
    """GET /api/loyalty/merchant/transactions/"""
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
    """GET /api/loyalty/merchant/punch-cards/"""
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    cards = MerchantPunchCard.objects.filter(merchant=merchant)
    return Response(MerchantPunchCardSerializer(cards, many=True).data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def merchant_punch_card_create(request):
    """POST /api/loyalty/merchant/punch-cards/"""
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
    """GET/PATCH /api/loyalty/merchant/punch-cards/<pk>/"""
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
    """GET /api/loyalty/punch-cards/?merchant=<id>"""
    merchant_id = request.query_params.get("merchant")
    if not merchant_id:
        return Response({"error": "merchant query param required"}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))
        
    cards = CustomerPunchCard.objects.filter(customer=customer, merchant_id=merchant_id, is_completed=False)
    completed = CustomerPunchCard.objects.filter(customer=customer, merchant_id=merchant_id, is_completed=True, is_redeemed=False)
    
    return Response({
        "active": CustomerPunchCardSerializer(cards, many=True).data,
        "completed": CustomerPunchCardSerializer(completed, many=True).data,
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def customer_punch_card_redeem(request, pk):
    """POST /api/loyalty/punch-cards/<pk>/redeem/"""
    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))
        
    try:
        card = CustomerPunchCard.objects.get(pk=pk, customer=customer)
    except CustomerPunchCard.DoesNotExist:
        return Response({"error": "Punch card not found"}, status=status.HTTP_404_NOT_FOUND)
        
    try:
        card.redeem()
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    return Response(CustomerPunchCardSerializer(card).data)


# ── Missions ──────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([AllowAny])
def mission_list(request):
    """
    GET /api/loyalty/missions/
    ?merchant=<id> — filter by merchant (optional)
    Returns all active missions.
    """
    missions = Mission.objects.filter(is_active=True).select_related("required_merchant")
    merchant_id = request.query_params.get("merchant")
    if merchant_id:
        missions = missions.filter(required_merchant_id=merchant_id)
    return Response(MissionSerializer(missions, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_missions(request):
    """
    GET /api/loyalty/missions/my-missions/
    ?merchant=<id> — optional filter
    Returns all active missions with the customer's current progress.
    """
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
    """
    GET /api/loyalty/missions/merchant/
    Merchant sees ALL their missions including inactive.
    """
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    missions = Mission.objects.filter(required_merchant=merchant)
    return Response(MissionSerializer(missions, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mission_create(request):
    """
    POST /api/loyalty/missions/
    Merchant creates a new mission.
    """
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
    """
    GET    /api/loyalty/missions/<id>/
    PATCH  /api/loyalty/missions/<id>/
    DELETE /api/loyalty/missions/<id>/
    """
    try:
        mission = Mission.objects.get(pk=pk)
    except Mission.DoesNotExist:
        return Response({"error": "Mission not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(MissionSerializer(mission).data)

    # Write operations — merchant only, must own the mission
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
    """
    GET /api/loyalty/rewards/
    ?merchant=<id> — filter by merchant (optional)
    Returns all active rewards.
    """
    rewards = Reward.objects.filter(is_active=True).select_related("merchant")
    merchant_id = request.query_params.get("merchant")
    if merchant_id:
        rewards = rewards.filter(merchant_id=merchant_id)
    return Response(RewardSerializer(rewards, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_rewards(request):
    """
    GET /api/loyalty/rewards/merchant/
    Merchant sees ALL their rewards including inactive.
    """
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    rewards = Reward.objects.filter(merchant=merchant)
    return Response(RewardSerializer(rewards, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reward_create(request):
    """
    POST /api/loyalty/rewards/
    Merchant creates a reward.
    """
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
    """
    GET    /api/loyalty/rewards/<id>/
    PATCH  /api/loyalty/rewards/<id>/
    DELETE /api/loyalty/rewards/<id>/
    """
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


# ── Redemptions ───────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def redeem_reward(request, pk):
    """
    POST /api/loyalty/rewards/<id>/redeem/
    Customer redeems a reward using their loyalty points.
    Generates a unique 6-char code and sets expiry to 10 minutes from now.
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

    # Decrease limited stock
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
        context_url="/merchant/loyalty",
        merchant_id=merchant.id,
        reward_id=reward.id,
    ))

    return Response(RedemptionSerializer(redemption).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_redemptions(request):
    """GET /api/loyalty/redemptions/ — customer's own redemption history."""
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
    """
    POST /api/loyalty/redemptions/confirm/
    Body: { "code": "ABC123" }
    Merchant scans / enters the code to confirm a redemption.
    """
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

    # Check expiry
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
    """
    GET /api/loyalty/redemptions/merchant/
    Returns redemptions for rewards belonging to the authenticated merchant.
    """
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
    """
    GET /api/loyalty/leaderboard/
    ?limit=10 — top N customers (default 10)
    ?merchant=<id> — required for meaningful ranking; uses merchant wallet balances

    Returns a ranked list scoped to a single merchant's wallets.
    """
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