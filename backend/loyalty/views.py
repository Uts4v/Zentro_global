"""
loyalty/views.py

All loyalty API endpoints — fully self-contained in Django, no Supabase.

Endpoints:
  GET/POST     /api/loyalty/rules/                    — merchant CRUD for loyalty rules
  GET          /api/loyalty/wallets/mine/             — customer's merchant-scoped wallet
  GET          /api/loyalty/wallets/                  — all wallets for customer
  GET          /api/loyalty/punch-cards/              — customer punch cards for a merchant
  POST         /api/loyalty/punch-cards/<id>/redeem/  — redeem a completed punch card
  GET          /api/loyalty/missions/                 — active missions list (public)
  GET          /api/loyalty/missions/my-missions/     — customer progress view
  GET          /api/loyalty/missions/merchant/        — merchant's missions
  POST         /api/loyalty/missions/create/          — merchant creates mission
  GET/PATCH/DELETE /api/loyalty/missions/<id>/        — mission detail
  GET          /api/loyalty/rewards/                  — active rewards (public)
  GET          /api/loyalty/rewards/merchant/         — merchant's rewards
  POST         /api/loyalty/rewards/create/           — merchant creates reward
  GET/PATCH/DELETE /api/loyalty/rewards/<id>/         — reward detail
  POST         /api/loyalty/rewards/<id>/redeem/      — customer redeems a reward
  GET          /api/loyalty/redemptions/              — customer's redemption history
  POST         /api/loyalty/redemptions/confirm/      — merchant confirms a code
  GET          /api/loyalty/redemptions/merchant/     — merchant's redemption history
  GET          /api/loyalty/transactions/             — customer point transactions
  GET          /api/loyalty/merchant/transactions/    — merchant point transactions
  GET          /api/loyalty/merchant/punch-cards/     — merchant punch card configs
  POST         /api/loyalty/merchant/punch-cards/create/
  GET/PATCH    /api/loyalty/merchant/punch-cards/<pk>/
  POST         /api/loyalty/merchant-profiles/join/  — customer joins a merchant
  GET          /api/loyalty/merchant-profiles/mine/  — customer's merchant profiles
  GET          /api/loyalty/leaderboard/             — top customers by points
  GET          /api/loyalty/specials/<slug>/         — public today's special
  GET/POST     /api/loyalty/merchant/specials/       — merchant specials CRUD
  GET/PATCH/DELETE /api/loyalty/merchant/specials/<pk>/
"""

import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from merchants.models import MerchantProfile
from orders.models import Order, OrderItem

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
    Notification,
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
    TodaySpecialSerializer,
    NotificationSerializer,
)
from .services import (
    join_merchant,
    get_or_create_wallet,
    deduct_wallet_points,
    create_notification,
)


# ── Helpers (MUST be defined before any view that uses them) ──────────────────

def get_customer_profile(user):
    """
    Return the CustomerProfile for this user, or raise PermissionError
    with a clear message.
    """
    from accounts.models import CustomerProfile

    # Case 1: happy path
    try:
        return user.customer_profile
    except CustomerProfile.DoesNotExist:
        pass
    except Exception:
        pass

    # Case 2: merchant account hitting a customer endpoint
    try:
        user.merchant_profile  # raises if doesn't exist
        raise PermissionError(
            f"You are logged in as a MERCHANT account ({user.email}). "
            "Customer loyalty endpoints require a customer account. "
            "Log in as your customer test account to use this page."
        )
    except PermissionError:
        raise
    except Exception:
        pass

    # Case 3: no profile at all
    raise PermissionError(
        f"No customer profile found for {user.email}. "
        "This account may not have completed customer registration."
    )


def get_merchant_profile(user) -> MerchantProfile:
    """Return the MerchantProfile or raise a descriptive PermissionError."""
    try:
        return user.merchant_profile
    except MerchantProfile.DoesNotExist:
        raise PermissionError(
            f"No merchant profile found for {user.email}."
        )


def _customer_error(detail: str):
    return Response({"error": detail}, status=status.HTTP_403_FORBIDDEN)


def _merchant_error(detail: str):
    return Response({"error": detail}, status=status.HTTP_403_FORBIDDEN)


# ── Today's Special ───────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([AllowAny])
def customer_today_special(request, slug):
    """GET /api/loyalty/specials/<slug>/ — public"""
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
    """GET/POST /api/loyalty/merchant/specials/"""
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
    """GET/PATCH/DELETE /api/loyalty/merchant/specials/<pk>/"""
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


# ── Merchant onboarding (customer ↔ merchant link) ────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def merchant_profile_join(request):
    """POST /api/loyalty/merchant-profiles/join/"""
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
    """GET /api/loyalty/merchant-profiles/mine/"""
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
    """GET /api/loyalty/wallets/mine/?merchant=<id>"""
    merchant_id = request.query_params.get("merchant")
    if not merchant_id:
        return Response(
            {"error": "merchant query param is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

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
    """GET /api/loyalty/wallets/"""
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


# ── Notifications ───────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notifications_list(request):
    """GET /api/loyalty/notifications/"""
    notifications = (
        Notification.objects
        .filter(user=request.user)
        .select_related("merchant")
        .order_by("-created_at")
    )
    return Response(NotificationSerializer(notifications, many=True).data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_unread_count(request):
    """GET /api/loyalty/notifications/unread-count/"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return Response({"unread_count": count})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def notification_mark_read(request, pk):
    """PATCH /api/loyalty/notifications/<pk>/read/"""
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
    except Notification.DoesNotExist:
        return Response({"error": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception:
        return Response({"error": "Unable to mark notification."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return Response(NotificationSerializer(notification).data)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def notification_mark_all_read(request):
    """PATCH /api/loyalty/notifications/read-all/"""
    try:
        updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"marked_read": updated})
    except Exception:
        return Response({"marked_read": 0})


# ── Loyalty Rules ─────────────────────────────────────────────────────────────

@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def loyalty_rules(request):
    """GET/PUT/PATCH /api/loyalty/rules/"""
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
        return Response(
            {"error": "merchant query param required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    transactions = PointTransaction.objects.filter(
        customer=customer, merchant_id=merchant_id
    ).order_by("-created_at")
    return Response(PointTransactionSerializer(transactions, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_point_transactions(request):
    """GET /api/loyalty/merchant/transactions/"""
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    transactions = PointTransaction.objects.filter(merchant=merchant).order_by("-created_at")
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
    """POST /api/loyalty/merchant/punch-cards/create/"""
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
        return Response(
            {"error": "merchant query param required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    active = CustomerPunchCard.objects.filter(
        customer=customer,
        merchant_id=merchant_id,
        is_completed=False,
    ).select_related("punch_card")

    completed = CustomerPunchCard.objects.filter(
        customer=customer,
        merchant_id=merchant_id,
        is_completed=True,
        is_redeemed=False,
    ).select_related("punch_card")

    return Response({
        "active": CustomerPunchCardSerializer(active, many=True).data,
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
    """GET /api/loyalty/missions/?merchant=<id>"""
    missions = Mission.objects.filter(is_active=True).select_related("required_merchant")
    merchant_id = request.query_params.get("merchant")
    if merchant_id:
        missions = missions.filter(required_merchant_id=merchant_id)
    return Response(MissionSerializer(missions, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_missions(request):
    """GET /api/loyalty/missions/my-missions/?merchant=<id>"""
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
    """GET /api/loyalty/missions/merchant/"""
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    missions = Mission.objects.filter(required_merchant=merchant)
    return Response(MissionSerializer(missions, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mission_create(request):
    """POST /api/loyalty/missions/create/"""
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
    """GET/PATCH/DELETE /api/loyalty/missions/<id>/"""
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
        return Response(
            {"error": "You can only edit your own missions."},
            status=status.HTTP_403_FORBIDDEN,
        )

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
    """GET /api/loyalty/rewards/?merchant=<id>"""
    rewards = Reward.objects.filter(is_active=True).select_related("merchant")
    merchant_id = request.query_params.get("merchant")
    if merchant_id:
        rewards = rewards.filter(merchant_id=merchant_id)
    return Response(RewardSerializer(rewards, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_rewards(request):
    """GET /api/loyalty/rewards/merchant/"""
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    rewards = Reward.objects.filter(merchant=merchant)
    return Response(RewardSerializer(rewards, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reward_create(request):
    """POST /api/loyalty/rewards/create/"""
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
    """GET/PATCH/DELETE /api/loyalty/rewards/<id>/"""
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
        return Response(
            {"error": "You can only edit your own rewards."},
            status=status.HTTP_403_FORBIDDEN,
        )

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
    """POST /api/loyalty/rewards/<id>/redeem/"""
    try:
        customer = get_customer_profile(request.user)
    except PermissionError as e:
        return _customer_error(str(e))

    try:
        reward = Reward.objects.select_for_update().get(pk=pk, is_active=True)
    except Reward.DoesNotExist:
        return Response(
            {"error": "Reward not found or inactive."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not reward.is_in_stock:
        return Response(
            {"error": "This reward is out of stock."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    wallet = get_or_create_wallet(customer, reward.merchant)
    try:
        deduct_wallet_points(
            wallet,
            reward.points_cost,
            transaction_type="REDEEMED",
            description=f"Redeemed reward: {reward.name}",
            reward=reward,
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

    # Create a real order so the merchant sees this in their normal orders queue.
    reward_order = Order.objects.create(
        customer=customer,
        merchant=reward.merchant,
        total_amount=0,
        points_earned=0,
        is_reward_order=True,
        status=Order.STATUS_PENDING,
        notes=f"Reward redemption — code {code}",
    )
    OrderItem.objects.create(
        order=reward_order,
        menu_item=None,
        name=f"🎁 {reward.name}",
        price=0,
        quantity=1,
        subtotal=0,
    )
    redemption.order = reward_order
    redemption.save(update_fields=["order"])

    create_notification(
        user=reward.merchant.user,
        merchant=reward.merchant,
        notification_type="new_order",
        title="Reward pickup order",
        message=f"{customer.full_name or customer.user.email} redeemed {reward.name}. Code: {code}.",
        context_url="/merchant/orders",
    )

    return Response(RedemptionSerializer(redemption).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_redemptions(request):
    """GET /api/loyalty/redemptions/"""
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
    """POST /api/loyalty/redemptions/confirm/"""
    try:
        merchant = get_merchant_profile(request.user)
    except PermissionError as e:
        return _merchant_error(str(e))

    code = (request.data.get("code") or "").strip().upper()
    if not code:
        return Response({"error": "code is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        redemption = Redemption.objects.select_related(
            "customer", "reward__merchant"
        ).get(
            code=code,
            status=Redemption.STATUS_PENDING,
            reward__merchant=merchant,
        )
    except Redemption.DoesNotExist:
        return Response(
            {"error": "Invalid code or already used."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if redemption.expires_at and timezone.now() > redemption.expires_at:
        redemption.status = Redemption.STATUS_EXPIRED
        redemption.save(update_fields=["status"])
        return Response(
            {"error": "This code has expired."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    redemption.status = Redemption.STATUS_CONFIRMED
    redemption.confirmed_at = timezone.now()
    redemption.save(update_fields=["status", "confirmed_at"])

    create_notification(
        user=redemption.customer.user,
        merchant=merchant,
        notification_type="redemption_confirmed",
        title="Reward confirmed",
        message=f"Your redemption for {redemption.reward.name} was confirmed.",
        context_url="/profile",
    )

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
    """GET /api/loyalty/redemptions/merchant/"""
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
    """GET /api/loyalty/leaderboard/?merchant=<id>&limit=10"""
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