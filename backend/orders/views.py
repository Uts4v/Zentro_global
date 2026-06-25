# orders/views.py
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Order, OrderItem
from .serializers import OrderSerializer, CreateOrderSerializer
from merchants.models import MenuItem, MerchantProfile
from accounts.models import CustomerProfile


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for order management."""

    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action in ["create_order", "my_orders", "store_orders", "update_status"]:
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Order.objects.none()
        if hasattr(user, "merchant_profile"):
            return Order.objects.filter(
                merchant=user.merchant_profile
            ).prefetch_related("items__menu_item").select_related("customer", "merchant")
        if hasattr(user, "customer_profile"):
            return Order.objects.filter(
                customer=user.customer_profile
            ).prefetch_related("items__menu_item").select_related("customer", "merchant")
        return Order.objects.none()

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def my_orders(self, request):
        """Get current customer's orders."""
        try:
            profile = request.user.customer_profile
        except CustomerProfile.DoesNotExist:
            return Response(
                {"error": "No customer profile found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        orders = Order.objects.filter(customer=profile).prefetch_related("items").order_by("-created_at")
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def store_orders(self, request):
        """Get current merchant's orders, optionally filtered by status."""
        try:
            profile = request.user.merchant_profile
        except MerchantProfile.DoesNotExist:
            return Response(
                {"error": "No merchant profile found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        qs = Order.objects.filter(merchant=profile).prefetch_related("items").order_by("-created_at")
        filter_status = request.query_params.get("status")
        if filter_status:
            qs = qs.filter(status=filter_status)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    @transaction.atomic
    def create_order(self, request):
        """Create a new order for the authenticated customer."""
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Get customer profile
        try:
            customer = request.user.customer_profile
        except CustomerProfile.DoesNotExist:
            return Response(
                {"error": "No customer profile found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get merchant
        try:
            merchant = MerchantProfile.objects.get(id=data["merchant_id"])
        except MerchantProfile.DoesNotExist:
            return Response(
                {"error": "Merchant not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not merchant.is_open:
            return Response(
                {"error": "This store is currently closed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build order items and calculate totals
        total_amount = 0
        points_earned = 0
        order_items = []

        for item_data in data["items"]:
            try:
                menu_item = MenuItem.objects.get(
                    id=item_data["menu_item_id"],
                    merchant=merchant,
                    is_available=True,
                )
            except MenuItem.DoesNotExist:
                return Response(
                    {"error": f"Menu item {item_data['menu_item_id']} not found or unavailable"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            quantity = item_data["quantity"]
            if quantity < 1:
                return Response(
                    {"error": "Quantity must be at least 1"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            subtotal = menu_item.price * quantity
            total_amount += subtotal

            if menu_item.loyalty_reward:
                points_earned += menu_item.points_per_item * quantity

            order_items.append({
                "menu_item": menu_item,
                "name": menu_item.name,
                "price": menu_item.price,
                "quantity": quantity,
                "subtotal": subtotal,
            })

        # Create the order — points are NOT awarded here.
        # They are awarded only when the merchant marks the order as "ready" or "completed".
        order = Order.objects.create(
            customer=customer,
            merchant=merchant,
            total_amount=total_amount,
            points_earned=points_earned,
            notes=data.get("notes", ""),
            status="pending",
        )

        for item in order_items:
            OrderItem.objects.create(order=order, **item)

        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated])
    def update_status(self, request, pk=None):
        """Update order status — merchant only."""
        order = self.get_object()

        try:
            merchant = request.user.merchant_profile
        except MerchantProfile.DoesNotExist:
            return Response(
                {"error": "Not authorized — merchant profile required"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if order.merchant != merchant:
            return Response(
                {"error": "This order does not belong to your store"},
                status=status.HTTP_403_FORBIDDEN,
            )

        new_status = request.data.get("status")
        valid_statuses = dict(Order.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            return Response(
                {"error": f"Invalid status. Choose from: {', '.join(valid_statuses)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Award points when merchant marks order as ready/completed (payment confirmed)
        if new_status in ("ready", "completed") and order.status not in ("ready", "completed"):
            customer = order.customer
            customer.loyalty_points += order.points_earned
            customer.total_orders += 1
            customer.save()

        order.status = new_status
        order.save()
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """Cancel an order — customer only, only if still pending."""
        order = self.get_object()

        try:
            customer = request.user.customer_profile
        except CustomerProfile.DoesNotExist:
            return Response({"error": "No customer profile."}, status=status.HTTP_403_FORBIDDEN)

        if order.customer != customer:
            return Response({"error": "Not your order."}, status=status.HTTP_403_FORBIDDEN)

        if order.status not in ("pending",):
            return Response(
                {"error": "Order can only be cancelled while pending"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = "cancelled"
        order.save()
        return Response(OrderSerializer(order).data)