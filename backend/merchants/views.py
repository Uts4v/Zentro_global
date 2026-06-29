# merchants/views.py
"""
Endpoints:
  GET    /api/merchants/                              — list all merchants (public)
  GET    /api/merchants/<id>/                         — merchant detail (public)
  GET    /api/merchants/slug/<slug>/                  — merchant by slug (public)
  GET    /api/merchants/me/                           — authenticated merchant's own profile
  PATCH  /api/merchants/me/update/                    — update own profile
  GET    /api/merchants/<id>/menu/                    — public menu for a merchant
  GET    /api/merchants/menu-items/                   — merchant's own items
  GET    /api/merchants/menu-items/my-items/          — merchant's own items (all)
  POST   /api/merchants/menu-items/                   — merchant creates item
  GET    /api/merchants/menu-items/<id>/              — item detail
  PATCH  /api/merchants/menu-items/<id>/              — merchant updates item
  DELETE /api/merchants/menu-items/<id>/              — merchant deletes item
  PATCH  /api/merchants/menu-items/<id>/toggle-availability/
  GET    /api/merchants/analytics/                    — merchant analytics summary
"""

import io
import base64
from datetime import timedelta

import qrcode
from django.db.models import Avg, Count, Sum
from django.utils import timezone
from django.utils.text import slugify

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import MerchantProfile, MenuItem
from .serializers import (
    MenuItemSerializer,
    MerchantProfileSerializer,
    MerchantPublicSerializer,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_merchant(user) -> MerchantProfile:
    try:
        return user.merchant_profile
    except MerchantProfile.DoesNotExist:
        raise PermissionError("No merchant profile found for this user.")


def _generate_qr(slug: str, request) -> str:
    """Generate a base64 QR code PNG pointing to the public merchant page."""
    customer_url = f"{request.scheme}://{request.get_host()}/m/{slug}"
    qr_img = qrcode.make(customer_url)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


# ── Merchant profile ──────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([AllowAny])
def merchant_list(request):
    """GET /api/merchants/ — all approved merchants (public)."""
    merchants = (
        MerchantProfile.objects
        .filter(is_approved=True)
        .order_by("business_name")   # ← fixed from store_name
    )
    return Response(MerchantPublicSerializer(merchants, many=True).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def merchant_detail(request, pk):
    """GET /api/merchants/<id>/ — single merchant detail (public)."""
    try:
        merchant = MerchantProfile.objects.get(pk=pk)
    except MerchantProfile.DoesNotExist:
        return Response(
            {"error": "Merchant not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(MerchantPublicSerializer(merchant).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def merchant_by_slug(request, slug):
    """GET /api/merchants/slug/<slug>/ — public merchant page by slug."""
    try:
        merchant = MerchantProfile.objects.get(slug=slug)
    except MerchantProfile.DoesNotExist:
        return Response(
            {"error": "Merchant not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(MerchantPublicSerializer(merchant).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_me(request):
    """GET /api/merchants/me/ — authenticated merchant's full profile."""
    try:
        merchant = _get_merchant(request.user)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
    return Response(MerchantProfileSerializer(merchant).data)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def merchant_update(request):
    """PATCH /api/merchants/me/update/ — update authenticated merchant's profile."""
    try:
        merchant = _get_merchant(request.user)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    serializer = MerchantProfileSerializer(
        merchant, data=request.data, partial=True
    )
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    instance = serializer.save()

    # Auto-generate slug from business_name if slug still empty after save
    if not instance.slug and instance.business_name:
        base_slug = slugify(instance.business_name)
        slug = base_slug
        counter = 1
        # Ensure uniqueness
        while MerchantProfile.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        instance.slug = slug
        instance.save(update_fields=["slug"])

    # Generate QR code once slug is set and no QR exists yet
    if instance.slug and not instance.qr_code:
        instance.qr_code = _generate_qr(instance.slug, request)
        instance.save(update_fields=["qr_code"])

    return Response(MerchantProfileSerializer(instance).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def merchant_menu(request, pk):
    """GET /api/merchants/<id>/menu/ — public menu for a specific merchant."""
    try:
        merchant = MerchantProfile.objects.get(pk=pk)
    except MerchantProfile.DoesNotExist:
        return Response(
            {"error": "Merchant not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    items = merchant.menu_items.filter(is_available=True).order_by("category", "name")
    return Response(MenuItemSerializer(items, many=True).data)


# ── Menu items ────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_menu_items(request):
    """GET /api/merchants/menu-items/my-items/ — merchant's full menu (all items)."""
    try:
        merchant = _get_merchant(request.user)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    items = MenuItem.objects.filter(merchant=merchant).order_by("category", "name")
    return Response(MenuItemSerializer(items, many=True).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def menu_item_list_create(request):
    """
    GET  /api/merchants/menu-items/ — merchant's items
    POST /api/merchants/menu-items/ — create new item
    """
    try:
        merchant = _get_merchant(request.user)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        items = MenuItem.objects.filter(merchant=merchant).order_by("category", "name")
        return Response(MenuItemSerializer(items, many=True).data)

    serializer = MenuItemSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save(merchant=merchant)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def menu_item_detail(request, pk):
    """
    GET    /api/merchants/menu-items/<id>/
    PATCH  /api/merchants/menu-items/<id>/
    DELETE /api/merchants/menu-items/<id>/
    """
    try:
        item = MenuItem.objects.get(pk=pk)
    except MenuItem.DoesNotExist:
        return Response(
            {"error": "Menu item not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        return Response(MenuItemSerializer(item).data)

    # Write operations — must own the item
    try:
        merchant = _get_merchant(request.user)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    if item.merchant != merchant:
        return Response(
            {"error": "You can only edit your own menu items."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "DELETE":
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = MenuItemSerializer(item, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response(serializer.data)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def toggle_availability(request, pk):
    """PATCH /api/merchants/menu-items/<id>/toggle-availability/"""
    try:
        item = MenuItem.objects.get(pk=pk)
    except MenuItem.DoesNotExist:
        return Response(
            {"error": "Menu item not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        merchant = _get_merchant(request.user)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    if item.merchant != merchant:
        return Response(
            {"error": "Not your item."},
            status=status.HTTP_403_FORBIDDEN,
        )

    item.is_available = not item.is_available
    item.save(update_fields=["is_available", "updated_at"])
    return Response(MenuItemSerializer(item).data)


# ── Analytics ─────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_analytics(request):
    """
    GET /api/merchants/analytics/?days=30
    """
    try:
        merchant = _get_merchant(request.user)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    days = int(request.query_params.get("days", 30))
    since = timezone.now() - timedelta(days=days)

    from orders.models import Order, OrderItem

    orders_qs = Order.objects.filter(
        merchant=merchant,
        created_at__gte=since,
    ).exclude(status=Order.STATUS_CANCELLED)

    agg = orders_qs.aggregate(
        total_revenue=Sum("total_amount"),
        total_orders=Count("id"),
        avg_order_value=Avg("total_amount"),
    )

    top_items = (
        OrderItem.objects
        .filter(order__merchant=merchant, order__created_at__gte=since)
        .exclude(order__status=Order.STATUS_CANCELLED)
        .values("name")
        .annotate(total_qty=Sum("quantity"), total_revenue=Sum("subtotal"))
        .order_by("-total_qty")[:10]
    )

    top_customers = (
        orders_qs
        .values("customer__full_name", "customer__user__email")
        .annotate(order_count=Count("id"), total_spent=Sum("total_amount"))
        .order_by("-order_count")[:10]
    )

    from django.db.models.functions import TruncDate
    daily = (
        orders_qs
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(revenue=Sum("total_amount"), orders=Count("id"))
        .order_by("date")
    )

    status_counts = (
        Order.objects
        .filter(merchant=merchant, created_at__gte=since)
        .values("status")
        .annotate(count=Count("id"))
    )

    return Response({
        "period_days": days,
        "total_revenue": agg["total_revenue"] or 0,
        "total_orders": agg["total_orders"] or 0,
        "avg_order_value": round(float(agg["avg_order_value"] or 0), 2),
        "top_items": list(top_items),
        "top_customers": [
            {
                "name": c["customer__full_name"] or c["customer__user__email"],
                "order_count": c["order_count"],
                "total_spent": c["total_spent"],
            }
            for c in top_customers
        ],
        "daily_revenue": [
            {
                "date": str(d["date"]),
                "revenue": d["revenue"],
                "orders": d["orders"],
            }
            for d in daily
        ],
        "orders_by_status": {s["status"]: s["count"] for s in status_counts},
    })