"""
orders/views.py

Order endpoints — fully Django-native, no Supabase.

Endpoints:
  GET  /api/orders/my-orders/            — customer's own orders
  GET  /api/orders/store-orders/         — merchant's orders (+ ?status= filter)
  POST /api/orders/create/               — customer places an order
  GET  /api/orders/<id>/                 — order detail
  PATCH /api/orders/<id>/update-status/  — merchant changes order status
  PATCH /api/orders/<id>/cancel/         — customer cancels pending order
"""

from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import CustomerProfile
from merchants.models import MerchantProfile, MenuItem
from loyalty.models import MerchantPunchCard, CustomerPunchCard, CustomerMission, Mission, CustomerMerchantProfile, Redemption
from loyalty.services import (
    create_notification,
    get_or_create_wallet,
    award_wallet_points,
    update_wallet_streak,
)

from .models import Order, OrderItem
from .serializers import OrderSerializer, CreateOrderSerializer


# ── Helpers ───────────────────────────────────────────────────────────────────

def _award_loyalty(order: Order):
    """
    Award merchant-scoped loyalty when an order is COMPLETED.
    Points, streak, tier, and missions are per merchant wallet — never global.
    """
    customer = order.customer
    wallet = get_or_create_wallet(customer, order.merchant)

    # 1. Points (merchant wallet only)
    if order.points_earned > 0:
        award_wallet_points(wallet, order.points_earned, transaction_type="EARNED", description=f"Points earned for Order #{order.id}", order=order)

    # 2. Order count + streak (merchant wallet)
    wallet.order_count += 1
    wallet.save(update_fields=["order_count", "updated_at"])
    streak_incremented = update_wallet_streak(wallet)

    # 3. Punch cards
    active_merchant_cards = MerchantPunchCard.objects.filter(
        merchant=order.merchant,
        is_active=True
    )

    for merchant_card in active_merchant_cards:
        # Get or create an active customer card for this type
        customer_card, _ = CustomerPunchCard.objects.get_or_create(
            customer=customer,
            punch_card=merchant_card,
            merchant=order.merchant,
            is_completed=False,
            defaults={"current_stamps": 0}
        )

        should_punch = False
        if merchant_card.mode == MerchantPunchCard.MODE_PER_ORDER:
            should_punch = True
        elif merchant_card.mode == MerchantPunchCard.MODE_PER_STREAK and streak_incremented:
            should_punch = True
            
        if should_punch:
            completed = customer_card.add_punch()
            if completed:
                try:
                    create_notification(
                        user=customer.user,
                        merchant=order.merchant,
                        notification_type="punch_card_completed",
                        title="Punch card completed",
                        message=f"Your punch card at {order.merchant.business_name} is complete. Claim your reward!",
                        context_url=f"/customer/order/{order.id}",
                    )
                except Exception:
                    # Don't let notification failures break order processing
                    pass

    # 4. Mission progress — order_count type
    _update_mission_progress(customer, order, wallet)


def _update_mission_progress(customer: CustomerProfile, order: Order, wallet):
    """Increment order_count missions for this merchant + general missions."""
    from loyalty.services import award_wallet_points as award_pts

    missions = Mission.objects.filter(
        is_active=True,
        mission_type="order_count",
    ).filter(
        required_merchant__in=[order.merchant, None]
    )

    for mission in missions:
        cm, _ = CustomerMission.objects.get_or_create(
            customer=customer,
            mission=mission,
        )
        if cm.is_completed:
            continue
        cm.current_count += 1
        if cm.current_count >= mission.target_count:
            cm.is_completed = True
            cm.completed_at = timezone.now()
            # Mission reward points go to the order's merchant wallet
            if mission.required_merchant_id:
                mission_wallet = get_or_create_wallet(customer, mission.required_merchant)
            else:
                mission_wallet = wallet
            award_pts(mission_wallet, mission.reward_points, transaction_type="MISSION_BONUS", description=f"Mission '{mission.title}' completed", mission=mission)
            try:
                create_notification(
                    user=customer.user,
                    merchant=mission.required_merchant or order.merchant,
                    notification_type="mission_completed",
                    title="Mission complete",
                    message=f"You completed '{mission.title}' and earned {mission.reward_points} points!",
                    context_url=f"/customer/order/{order.id}",
                )
            except Exception:
                pass
        cm.save()


# ── Views ─────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_orders(request):
    """GET /api/orders/my-orders/ — customer's own order history."""
    try:
        customer = request.user.customer_profile
    except CustomerProfile.DoesNotExist:
        return Response({"error": "No customer profile found."}, status=status.HTTP_404_NOT_FOUND)

    orders = (
        Order.objects
        .filter(customer=customer)
        .prefetch_related("items__menu_item")
        .select_related("merchant")
        .order_by("-created_at")
    )
    return Response(OrderSerializer(orders, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def store_orders(request):
    """GET /api/orders/store-orders/ — merchant's incoming orders. ?status= for filtering."""
    try:
        merchant = request.user.merchant_profile
    except MerchantProfile.DoesNotExist:
        return Response({"error": "No merchant profile found."}, status=status.HTTP_404_NOT_FOUND)

    qs = (
        Order.objects
        .filter(merchant=merchant)
        .prefetch_related("items__menu_item")
        .select_related("customer__user")
        .order_by("-created_at")
    )

    filter_status = request.query_params.get("status")
    if filter_status:
        qs = qs.filter(status=filter_status)

    return Response(OrderSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def create_order(request):
    """
    POST /api/orders/create/
    Body: { merchant_id, items: [{menu_item_id, quantity}], notes? }
    """
    serializer = CreateOrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # Customer profile
    try:
        customer = request.user.customer_profile
    except CustomerProfile.DoesNotExist:
        return Response({"error": "No customer profile found."}, status=status.HTTP_404_NOT_FOUND)

    # Merchant
    try:
        merchant = MerchantProfile.objects.get(id=data["merchant_id"])
    except MerchantProfile.DoesNotExist:
        return Response({"error": "Merchant not found."}, status=status.HTTP_404_NOT_FOUND)

    if not merchant.is_open:
        return Response({"error": "This store is currently closed."}, status=status.HTTP_400_BAD_REQUEST)

    # Customer must be linked to this merchant (QR / slug onboarding)
    if not CustomerMerchantProfile.objects.filter(
        customer=customer,
        merchant=merchant,
        status=CustomerMerchantProfile.STATUS_ACTIVE,
    ).exists():
        return Response(
            {"error": "Join this merchant before placing an order."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Build order items
    total_amount = 0
    points_earned = 0
    order_items_data = []

    for item_data in data["items"]:
        try:
            menu_item = MenuItem.objects.get(
                id=item_data["menu_item_id"],
                merchant=merchant,
                is_available=True,
            )
        except MenuItem.DoesNotExist:
            return Response(
                {"error": f"Menu item {item_data['menu_item_id']} not found or unavailable."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quantity = item_data["quantity"]
        subtotal = menu_item.price * quantity
        total_amount += subtotal

        if menu_item.loyalty_reward:
            points_earned += menu_item.points_per_item * quantity

        order_items_data.append({
            "menu_item": menu_item,
            "name": menu_item.name,
            "price": menu_item.price,
            "quantity": quantity,
            "subtotal": subtotal,
        })

    # Create order (status = pending; points NOT awarded yet)
    order = Order.objects.create(
        customer=customer,
        merchant=merchant,
        total_amount=total_amount,
        points_earned=points_earned,
        notes=data.get("notes", ""),
        status=Order.STATUS_PENDING,
    )

    for item in order_items_data:
        OrderItem.objects.create(order=order, **item)
    try:
        create_notification(
            user=merchant.user,
            merchant=merchant,
            notification_type="new_order",
            title="New order received",
            message=f"Order #{order.id} has been placed by {customer.full_name or customer.user.email}.",
            context_url="/merchant/orders",
        )
    except Exception:
        pass

    return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def order_detail(request, pk):
    """GET /api/orders/<id>/ — single order details."""
    try:
        order = (
            Order.objects
            .prefetch_related("items__menu_item")
            .select_related("customer__user", "merchant")
            .get(pk=pk)
        )
    except Order.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

    # Access control: only the customer or the merchant can view
    user = request.user
    is_owner = (
        (hasattr(user, "customer_profile") and order.customer == user.customer_profile)
        or (hasattr(user, "merchant_profile") and order.merchant == user.merchant_profile)
    )
    if not is_owner and not user.is_staff:
        return Response({"error": "Not authorised."}, status=status.HTTP_403_FORBIDDEN)

    return Response(OrderSerializer(order).data)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def update_order_status(request, pk):
    """
    PATCH /api/orders/<id>/update-status/
    Body: { "status": "confirmed" | "preparing" | "ready" | "completed" | "cancelled" }
    Only the merchant who owns the order can update its status.
    Merchant-scoped points + punch card are awarded when status becomes "completed".
    """
    try:
        order = Order.objects.select_related("customer", "merchant").get(pk=pk)
    except Order.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        merchant = request.user.merchant_profile
    except MerchantProfile.DoesNotExist:
        return Response({"error": "Merchant access required."}, status=status.HTTP_403_FORBIDDEN)

    if order.merchant != merchant:
        return Response({"error": "This order does not belong to your store."}, status=status.HTTP_403_FORBIDDEN)

    new_status = request.data.get("status")
    valid_statuses = dict(Order.STATUS_CHOICES).keys()
    if new_status not in valid_statuses:
        return Response(
            {"error": f"Invalid status. Choose from: {', '.join(valid_statuses)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    previous_status = order.status

    # Award loyalty once on first transition INTO "completed" — skip for reward pickup orders,
    # since points were already deducted at redemption time.
    if (
        new_status == Order.STATUS_COMPLETED
        and not order.loyalty_awarded
        and not order.is_reward_order
        and previous_status != Order.STATUS_CANCELLED
    ):
        _award_loyalty(order)
        order.loyalty_awarded = True

    # If this is a reward pickup order being completed, auto-confirm the linked redemption.
    if new_status == Order.STATUS_COMPLETED and order.is_reward_order:
        try:
            redemption = order.redemption
        except Redemption.DoesNotExist:
            redemption = None

        if redemption and redemption.status == redemption.STATUS_PENDING:
            redemption.status = redemption.STATUS_CONFIRMED
            redemption.confirmed_at = timezone.now()
            redemption.save(update_fields=["status", "confirmed_at"])
            create_notification(
                user=order.customer.user,
                merchant=order.merchant,
                notification_type="redemption_confirmed",
                title="Reward confirmed",
                message=f"Your redemption for {redemption.reward.name} was confirmed.",
                context_url="/profile",
            )

    order.status = new_status
    order.save(update_fields=["status", "loyalty_awarded", "updated_at"])

    try:
        create_notification(
            user=order.customer.user,
            merchant=order.merchant,
            notification_type="order_status",
            title="Order status updated",
            message=f"Your order #{order.id} is now {new_status}.",
            context_url=f"/orders/{order.id}",
        )
    except Exception:
        pass

    return Response(OrderSerializer(order).data)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def cancel_order(request, pk):
    """
    PATCH /api/orders/<id>/cancel/
    Customer cancels a pending order.
    """
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        customer = request.user.customer_profile
    except CustomerProfile.DoesNotExist:
        return Response({"error": "No customer profile."}, status=status.HTTP_403_FORBIDDEN)

    if order.customer != customer:
        return Response({"error": "Not your order."}, status=status.HTTP_403_FORBIDDEN)

    if order.status != Order.STATUS_PENDING:
        return Response(
            {"error": "Only pending orders can be cancelled."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    order.status = Order.STATUS_CANCELLED
    order.save(update_fields=["status", "updated_at"])
    try:
        create_notification(
            user=order.merchant.user,
            merchant=order.merchant,
            notification_type="order_status",
            title="Order cancelled",
            message=f"Order #{order.id} was cancelled by the customer.",
            context_url="/merchant/orders",
        )
    except Exception:
        pass

    return Response(OrderSerializer(order).data)