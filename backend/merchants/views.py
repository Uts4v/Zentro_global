# merchants/views.py
"""
Endpoints:
  GET    /api/merchants/                              — list all merchants (public)
  GET    /api/merchants/nearby/                       — nearby merchants (public)
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
import math
from datetime import timedelta

import qrcode
from django.conf import settings
from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.text import slugify

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import MerchantProfile, MenuItem, MerchantTable
from .serializers import (
    MenuItemSerializer,
    MerchantProfileSerializer,
    MerchantPublicSerializer,
    MerchantDiscoverySerializer,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_merchant(user) -> MerchantProfile:
    try:
        return user.merchant_profile
    except MerchantProfile.DoesNotExist:
        raise PermissionError("No merchant profile found for this user.")


def _generate_qr(slug: str, request) -> str:
    """Generate a base64 QR code PNG pointing to the public merchant page."""
    frontend_url = getattr(settings, "FRONTEND_URL", f"{request.scheme}://{request.get_host()}")
    customer_url = f"{frontend_url.rstrip('/')}/m/{slug}"
    qr_img = qrcode.make(customer_url)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def _haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lng points, in kilometers."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


# ── Merchant profile ──────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([AllowAny])
def merchant_list(request):
    """GET /api/merchants/ — all approved merchants (public)."""
    merchants = MerchantProfile.objects.filter(is_approved=True).order_by("business_name")
    return Response(MerchantPublicSerializer(merchants, many=True).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def merchant_discovery_nearby(request):
    """
    GET /api/merchants/nearby/?lat=<float>&lng=<float>
    Public discovery feed for the map + nearby list.
    """
    lat_param = request.query_params.get("lat")
    lng_param = request.query_params.get("lng")

    user_lat = user_lng = None
    if lat_param is not None and lng_param is not None:
        try:
            user_lat = float(lat_param)
            user_lng = float(lng_param)
        except ValueError:
            return Response(
                {"error": "lat and lng must be valid numbers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    merchants = MerchantProfile.objects.filter(is_approved=True)

    distances = {}
    if user_lat is not None and user_lng is not None:
        for m in merchants:
            if m.latitude is not None and m.longitude is not None:
                distances[m.id] = _haversine_km(
                    user_lat, user_lng, float(m.latitude), float(m.longitude)
                )
        merchants = sorted(merchants, key=lambda m: distances.get(m.id, float("inf")))
    else:
        merchants = merchants.order_by("business_name")

    serializer = MerchantDiscoverySerializer(
        merchants, many=True, context={"distances": distances}
    )
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def merchant_detail(request, pk):
    """GET /api/merchants/<id>/ — single merchant detail (public)."""
    try:
        merchant = MerchantProfile.objects.get(pk=pk)
    except MerchantProfile.DoesNotExist:
        return Response({"error": "Merchant not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(MerchantPublicSerializer(merchant).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def merchant_by_slug(request, slug):
    """GET /api/merchants/slug/<slug>/ — public merchant page by slug."""
    try:
        merchant = MerchantProfile.objects.get(slug=slug)
    except MerchantProfile.DoesNotExist:
        return Response({"error": "Merchant not found."}, status=status.HTTP_404_NOT_FOUND)
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

    serializer = MerchantProfileSerializer(merchant, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    instance = serializer.save()

    # Auto-generate slug from business_name if slug still empty after save
    if not instance.slug and instance.business_name:
        base_slug = slugify(instance.business_name)
        slug = base_slug
        counter = 1
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def merchant_regenerate_qr(request):
    """POST /api/merchants/me/regenerate-qr/ — force-regenerate the merchant QR code."""
    try:
        merchant = _get_merchant(request.user)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    if not merchant.slug:
        return Response({"error": "Merchant slug not set."}, status=status.HTTP_400_BAD_REQUEST)

    merchant.qr_code = _generate_qr(merchant.slug, request)
    merchant.save(update_fields=["qr_code"])
    return Response({"qr_code": merchant.qr_code})


@api_view(["GET"])
@permission_classes([AllowAny])
def merchant_menu(request, pk):
    """GET /api/merchants/<id>/menu/ — public menu for a specific merchant."""
    try:
        merchant = MerchantProfile.objects.get(pk=pk)
    except MerchantProfile.DoesNotExist:
        return Response({"error": "Merchant not found."}, status=status.HTTP_404_NOT_FOUND)
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
        return Response({"error": "Menu item not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(MenuItemSerializer(item).data)

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
        return Response({"error": "Menu item not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        merchant = _get_merchant(request.user)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    if item.merchant != merchant:
        return Response({"error": "Not your item."}, status=status.HTTP_403_FORBIDDEN)

    item.is_available = not item.is_available
    item.save(update_fields=["is_available", "updated_at"])
    return Response(MenuItemSerializer(item).data)


# ── Analytics ─────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_analytics(request):
    """GET /api/merchants/analytics/?days=30"""
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


# ── Table management ──────────────────────────────────────────────────────────

from django.db import transaction as db_transaction
from rest_framework import serializers as _serializers


class _TableSerializer(_serializers.ModelSerializer):
    class Meta:
        model = MerchantTable
        fields = [
            "id", "name", "table_number", "public_token",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "public_token", "created_at", "updated_at"]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def merchant_tables(request):
    """GET /api/merchants/tables/ — list merchant's tables."""
    try:
        merchant = _get_merchant(request.user)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    tables = MerchantTable.objects.filter(merchant=merchant).order_by("table_number")
    return Response(_TableSerializer(tables, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def merchant_tables_create(request):
    """POST /api/merchants/tables/ — create a single table."""
    try:
        merchant = _get_merchant(request.user)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    serializer = _TableSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Prevent duplicate table numbers
    table_number = serializer.validated_data["table_number"]
    if MerchantTable.objects.filter(merchant=merchant, table_number=table_number).exists():
        return Response(
            {"error": f"Table number {table_number} already exists."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer.save(merchant=merchant)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def merchant_table_detail(request, pk):
    """PATCH /api/merchants/tables/{id}/ — update a table."""
    try:
        merchant = _get_merchant(request.user)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    try:
        table = MerchantTable.objects.get(pk=pk, merchant=merchant)
    except MerchantTable.DoesNotExist:
        return Response({"error": "Table not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = _TableSerializer(table, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Check for duplicate table number if changing
    new_number = serializer.validated_data.get("table_number")
    if new_number is not None and new_number != table.table_number:
        if MerchantTable.objects.filter(
            merchant=merchant, table_number=new_number
        ).exclude(pk=pk).exists():
            return Response(
                {"error": f"Table number {new_number} already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    serializer.save()
    return Response(serializer.data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def merchant_table_delete(request, pk):
    """DELETE /api/merchants/tables/{id}/ — delete a table."""
    try:
        merchant = _get_merchant(request.user)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    try:
        table = MerchantTable.objects.get(pk=pk, merchant=merchant)
    except MerchantTable.DoesNotExist:
        return Response({"error": "Table not found."}, status=status.HTTP_404_NOT_FOUND)

    table.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def merchant_tables_generate(request):
    """POST /api/merchants/tables/generate/ — bulk-generate tables."""
    try:
        merchant = _get_merchant(request.user)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    count = request.data.get("count")
    name_prefix = request.data.get("name_prefix", "Table")

    if not isinstance(count, int) or count < 1 or count > 200:
        return Response(
            {"error": "Count must be an integer between 1 and 200."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Find the highest existing table number
    max_number = (
        MerchantTable.objects.filter(merchant=merchant)
        .order_by("-table_number")
        .values_list("table_number", flat=True)
        .first()
    ) or 0

    with db_transaction.atomic():
        tables = []
        for i in range(1, count + 1):
            num = max_number + i
            name = f"{name_prefix} {num}"
            tables.append(
                MerchantTable(
                    merchant=merchant,
                    name=name,
                    table_number=num,
                )
            )
        MerchantTable.objects.bulk_create(tables)

    return Response(
        _TableSerializer(tables, many=True).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def merchant_table_regenerate_qr(request, pk):
    """POST /api/merchants/tables/{id}/regenerate-qr/ — regenerate QR token."""
    try:
        merchant = _get_merchant(request.user)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    try:
        table = MerchantTable.objects.get(pk=pk, merchant=merchant)
    except MerchantTable.DoesNotExist:
        return Response({"error": "Table not found."}, status=status.HTTP_404_NOT_FOUND)

    table.regenerate_token()
    return Response(_TableSerializer(table).data)


# ── Public table resolution ───────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([AllowAny])
def public_resolve_table(request, slug, public_token):
    """
    GET /api/public/merchants/{slug}/tables/{public_token}/
    Resolves a public table QR token to merchant + table info.
    """
    try:
        merchant = MerchantProfile.objects.get(slug=slug, is_approved=True)
    except MerchantProfile.DoesNotExist:
        return Response(
            {"error": "Merchant not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not merchant.table_ordering_enabled:
        return Response(
            {"error": "Table ordering is not enabled for this merchant."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        table = MerchantTable.objects.get(
            public_token=public_token,
            merchant=merchant,
            is_active=True,
        )
    except MerchantTable.DoesNotExist:
        return Response(
            {"error": "Invalid or inactive table QR code."},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response({
        "merchant": {
            "id": merchant.id,
            "name": merchant.business_name,
            "slug": merchant.slug,
            "logo": merchant.logo_url,
        },
        "table": {
            "id": table.id,
            "name": table.name,
            "table_number": table.table_number,
            "public_token": table.public_token,
        },
    })