# orders/serializers.py
from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "menu_item", "name", "price", "quantity", "subtotal"]
        read_only_fields = ["id"]


class OrderSerializer(serializers.ModelSerializer):
    items         = OrderItemSerializer(many=True, read_only=True)
    merchant_name = serializers.CharField(source="merchant.business_name", read_only=True)
    customer_name = serializers.CharField(source="customer.full_name",     read_only=True)
    merchant_id   = serializers.IntegerField(source="merchant.id",         read_only=True)

    # Display helpers for redemption orders — null for regular orders
    reward_name = serializers.CharField(
        source="reward_redemption.reward.name", read_only=True, default=None
    )
    punch_card_name = serializers.CharField(
        source="punch_card_redemption.punch_card.name", read_only=True, default=None
    )

    class Meta:
        model = Order
        fields = [
            "id", "customer", "customer_name",
            "merchant", "merchant_id", "merchant_name",
            "status", "order_type",
            "total_amount", "points_earned",
            "notes", "items",
            "cancellation_reason", "cancelled_by",
            "reward_name", "punch_card_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CreateOrderItemSerializer(serializers.Serializer):
    menu_item_id = serializers.IntegerField()
    quantity     = serializers.IntegerField(min_value=1)


class CreateOrderSerializer(serializers.Serializer):
    merchant_id = serializers.IntegerField()
    items       = CreateOrderItemSerializer(many=True)
    notes       = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Order must contain at least one item.")
        return value