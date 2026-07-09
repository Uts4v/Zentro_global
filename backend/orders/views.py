# orders/views.py
import logging

from django.db import transaction
from django.utils import timezone

from datetime import timedelta
from django.db.models import Q
from accounts.models import CustomerProfile

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from merchants.models import MerchantProfile, MenuItem
from loyalty.models import (
    MerchantPunchCard, CustomerPunchCard,
    CustomerMission, Mission, CustomerMerchantProfile,
)
from loyalty.services import (
    get_or_create_wallet, award_wallet_points, update_wallet_streak,
)
from notifications.services import send_notification
from notifications.models import Notification

from .models import Order, OrderItem
from .serializers import OrderSerializer, CreateOrderSerializer

logger = logging.getLogger(__name__)


def _notify_safe(**kwargs):
    try:
        send_notification(**kwargs)
    except Exception:
        logger.exception("Failed to send notification (order flow continues)")


def _award_loyalty(order: Order):
    customer = order.customer
    wallet   = get_or_create_wallet(customer, order.merchant)

    if order.points_earned > 0:
        award_wallet_points(
            wallet, order.points_earned,
            transaction_type="EARNED",
            description=f"Points earned for Order #{order.id}",
            order=order,
        )

    wallet.order_count += 1
    wallet.save(update_fields=["order_count", "updated_at"])
    streak_incremented = update_wallet_streak(wallet)

    # Punch cards
    for merchant_card in MerchantPunchCard.objects.filter(
        merchant=order.merchant, is_active=True
    ):
        customer_card, _ = CustomerPunchCard.objects.get_or_create(
            customer=customer,
            punch_card=merchant_card,
            merchant=order.merchant,
            is_completed=False,
            defaults={"current_stamps": 0},
        )
        should_punch = (
            merchant_card.mode == MerchantPunchCard.MODE_PER_ORDER
            or (merchant_card.mode == MerchantPunchCard.MODE_PER_STREAK and streak_incremented)
        )
        if should_punch:
            completed = customer_card.add_punch()
            if completed:
                # Notify customer their punch card is complete
                transaction.on_commit(lambda: _notify_safe(
                    user=customer.user,
                    title="Punch card complete! 🎉",
                    message=f"Show your card to claim: {merchant_card.reward_text}",
                    notification_type=Notification.TYPE_PUNCH_CARD,
                    merchant_name=order.merchant.business_name,
                    context_url=f"/customer/merchant/{order.merchant.slug}",
                    merchant_id=order.merchant.id,
                ))

    _update_mission_progress(customer, order, wallet, streak_incremented)


def _update_mission_progress(customer, order, wallet, streak_incremented):
    from loyalty.services import award_wallet_points as award_pts

    missions = Mission.objects.filter(
        is_active=True,
        mission_type__in=["order_count", "spend_amount", "visit_streak"],
    ).filter(required_merchant__in=[order.merchant, None])

    for mission in missions:
        if mission.mission_type == "visit_streak" and not streak_incremented:
            continue

        cm, _ = CustomerMission.objects.get_or_create(
            customer=customer, mission=mission,
        )
        if cm.is_completed:
            continue

        if mission.mission_type == "spend_amount":
            cm.current_count += int(order.total_amount)
        else:
            cm.current_count += 1

        if cm.current_count >= mission.target_count:
            cm.is_completed  = True
            cm.completed_at  = timezone.now()
            mission_wallet   = (
                get_or_create_wallet(customer, mission.required_merchant)
                if mission.required_merchant_id else wallet
            )
            award_pts(
                mission_wallet, mission.reward_points,
                transaction_type="MISSION_BONUS",
                description=f"Mission '{mission.title}' completed",
                mission=mission,
            )
            transaction.on_commit(lambda: _notify_safe(
                user=customer.user,
                title=f"Mission complete: {mission.title} 🎯",
                message=f"You earned {mission.reward_points} bonus points!",
                notification_type=Notification.TYPE_MISSION_COMPLETE,
                merchant_name=order.merchant.business_name,
                context_url=f"/customer/merchant/{order.merchant.slug}",
                merchant_id=order.merchant.id,
            ))
        cm.save()


# ── Views ─────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_orders(request):
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
    serializer = CreateOrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    try:
        customer = request.user.customer_profile
    except CustomerProfile.DoesNotExist:
        return Response({"error": "No customer profile found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        merchant = MerchantProfile.objects.get(id=data["merchant_id"])
    except MerchantProfile.DoesNotExist:
        return Response({"error": "Merchant not found."}, status=status.HTTP_404_NOT_FOUND)

    if not merchant.is_open:
        return Response({"error": "This store is currently closed."}, status=status.HTTP_400_BAD_REQUEST)

    if not CustomerMerchantProfile.objects.filter(
        customer=customer, merchant=merchant,
        status=CustomerMerchantProfile.STATUS_ACTIVE,
    ).exists():
        return Response(
            {"error": "Join this merchant before placing an order."},
            status=status.HTTP_403_FORBIDDEN,
        )

    total_amount   = 0
    points_earned  = 0
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

        quantity  = item_data["quantity"]
        subtotal  = menu_item.price * quantity
        total_amount += subtotal

        if menu_item.loyalty_reward:
            points_earned += menu_item.points_per_item * quantity

        order_items_data.append({
            "menu_item": menu_item,
            "name":      menu_item.name,
            "price":     menu_item.price,
            "quantity":  quantity,
            "subtotal":  subtotal,
        })

    order = Order.objects.create(
        customer=customer,
        merchant=merchant,
        total_amount=total_amount,
        points_earned=points_earned,
        notes=data.get("notes", ""),
        status=Order.STATUS_PENDING,
        order_type=Order.ORDER_TYPE_REGULAR,
    )

    for item in order_items_data:
        OrderItem.objects.create(order=order, **item)

    transaction.on_commit(lambda: _notify_safe(
        user=merchant.user,
        title="New order received 🔔",
        message=f"Order #{order.id} from {customer.full_name or 'Customer'} — NPR {total_amount}",
        notification_type=Notification.TYPE_NEW_ORDER,
        merchant_name=merchant.business_name,
        context_url="/merchant/orders",
        order_id=order.id,
        merchant_id=merchant.id,
    ))

    return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def order_detail(request, pk):
    try:
        order = (
            Order.objects
            .prefetch_related("items__menu_item")
            .select_related("customer__user", "merchant")
            .get(pk=pk)
        )
    except Order.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

    user     = request.user
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
    try:
        order = Order.objects.select_related("customer__user", "merchant").get(pk=pk)
    except Order.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        merchant = request.user.merchant_profile
    except MerchantProfile.DoesNotExist:
        return Response({"error": "Merchant access required."}, status=status.HTTP_403_FORBIDDEN)

    if order.merchant != merchant:
        return Response({"error": "This order does not belong to your store."}, status=status.HTTP_403_FORBIDDEN)

    new_status = request.data.get("status")
    if new_status not in dict(Order.STATUS_CHOICES):
        return Response(
            {"error": f"Invalid status. Choose from: {', '.join(dict(Order.STATUS_CHOICES).keys())}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if (
        new_status == Order.STATUS_COMPLETED
        and not order.loyalty_awarded
        and order.status != Order.STATUS_CANCELLED
    ):
        _award_loyalty(order)
        order.loyalty_awarded = True

    order.status = new_status
    order.save(update_fields=["status", "loyalty_awarded", "updated_at"])

    status_msg = {
        "confirmed": "Your order has been accepted! ✅",
        "preparing": "Your order is being prepared ☕",
        "ready":     "Your order is ready for pickup! 🔔",
        "completed": "Order complete — enjoy! 🎉",
    }.get(new_status, f"Your order is now {new_status}.")

    transaction.on_commit(lambda: _notify_safe(
        user=order.customer.user,
        title="Order update",
        message=status_msg,
        notification_type=Notification.TYPE_ORDER_UPDATE,
        merchant_name=order.merchant.business_name,
        context_url=f"/orders/{order.id}",
        order_id=order.id,
        merchant_id=order.merchant.id,
    ))

    return Response(OrderSerializer(order).data)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def cancel_order(request, pk):
    try:
        order = Order.objects.select_related(
            "customer__user", "merchant__user"
        ).get(pk=pk)
    except Order.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

    reason = request.data.get("reason", "")
    user   = request.user

    # Determine who is cancelling
    is_customer = hasattr(user, "customer_profile") and order.customer == user.customer_profile
    is_merchant = hasattr(user, "merchant_profile") and order.merchant == user.merchant_profile

    if not is_customer and not is_merchant:
        return Response({"error": "Not authorised."}, status=status.HTTP_403_FORBIDDEN)

    # Customers can only cancel pending orders
    if is_customer and order.status != Order.STATUS_PENDING:
        return Response(
            {"error": "You can only cancel pending orders."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Merchants can cancel pending or confirmed orders
    if is_merchant and order.status not in [Order.STATUS_PENDING, Order.STATUS_CONFIRMED]:
        return Response(
            {"error": "You can only cancel pending or confirmed orders."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    order.status       = Order.STATUS_CANCELLED
    order.cancelled_by = Order.CANCELLED_BY_CUSTOMER if is_customer else Order.CANCELLED_BY_MERCHANT
    order.cancellation_reason = reason
    order.save(update_fields=["status", "cancelled_by", "cancellation_reason", "updated_at"])

    reason_label = dict(Order.CANCEL_REASON_CHOICES).get(reason, "")

    if is_customer:
        msg = f"Order #{order.id} was cancelled by customer"
        if reason_label:
            msg += f" — {reason_label}"
        transaction.on_commit(lambda: _notify_safe(
            user=order.merchant.user,
            title="Order cancelled",
            message=msg,
            notification_type=Notification.TYPE_ORDER_UPDATE,
            merchant_name=order.merchant.business_name,
            context_url="/merchant/orders",
            order_id=order.id,
            merchant_id=order.merchant.id,
        ))
    else:
        msg = f"Your order at {order.merchant.business_name} was cancelled"
        if reason_label:
            msg += f" — {reason_label}"
        transaction.on_commit(lambda: _notify_safe(
            user=order.customer.user,
            title="Order cancelled",
            message=msg,
            notification_type=Notification.TYPE_ORDER_UPDATE,
            merchant_name=order.merchant.business_name,
            context_url=f"/orders/{order.id}",
            order_id=order.id,
            merchant_id=order.merchant.id,
        ))

    return Response(OrderSerializer(order).data)

# Add these two views to orders/views.py
# They enforce the 1-month (customer) and 2-month (merchant) limits
# and support search + status filtering via query params


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_order_history(request):
    
    try:
        customer = request.user.customer_profile
    except CustomerProfile.DoesNotExist:
        return Response({"error": "No customer profile."}, status=403)

    one_month_ago = timezone.now() - timedelta(days=30)
    qs = Order.objects.filter(
        customer=customer,
        created_at__gte=one_month_ago,
    ).prefetch_related("items").select_related("merchant").order_by("-created_at")

    search = request.query_params.get("search", "").strip()
    if search:
        qs = qs.filter(
            Q(id__icontains=search) |
            Q(items__name__icontains=search) |
            Q(merchant__business_name__icontains=search)
        ).distinct()

    status_filter = request.query_params.get("status", "").strip()
    if status_filter:
        qs = qs.filter(status=status_filter)

    from .serializers import OrderSerializer
    return Response(OrderSerializer(qs, many=True).data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def customer_clear_order_history(request):
    """
    DELETE /api/orders/history/clear/
    Soft-clears: marks orders as hidden from history (doesn't delete DB rows).
    If you want hard delete, swap the update() for delete().
    """
    from accounts.models import CustomerProfile
    try:
        customer = request.user.customer_profile
    except CustomerProfile.DoesNotExist:
        return Response({"error": "No customer profile."}, status=403)

    one_month_ago = timezone.now() - timedelta(days=30)
    # Hard delete old orders from customer's history view
    Order.objects.filter(
        customer=customer,
        created_at__gte=one_month_ago,
        status__in=["completed", "cancelled"],
    ).delete()

    return Response({"status": "cleared"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_order_history(request):
    """
    GET /api/orders/merchant-history/
    Returns merchant orders from the last 60 days.
    Query params:
      ?search=<text>    — filter by order id, customer name, or item name
      ?status=<status>  — filter by status
    """
    from merchants.models import MerchantProfile
    try:
        merchant = request.user.merchant_profile
    except MerchantProfile.DoesNotExist:
        return Response({"error": "No merchant profile."}, status=403)

    two_months_ago = timezone.now() - timedelta(days=60)
    qs = Order.objects.filter(
        merchant=merchant,
        created_at__gte=two_months_ago,
    ).prefetch_related("items").select_related("customer__user").order_by("-created_at")

    search = request.query_params.get("search", "").strip()
    if search:
        qs = qs.filter(
            Q(id__icontains=search) |
            Q(items__name__icontains=search) |
            Q(customer__full_name__icontains=search) |
            Q(customer__user__email__icontains=search)
        ).distinct()

    status_filter = request.query_params.get("status", "").strip()
    if status_filter:
        qs = qs.filter(status=status_filter)

    from .serializers import OrderSerializer
    return Response(OrderSerializer(qs, many=True).data)