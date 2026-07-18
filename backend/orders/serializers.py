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
    customer_name = serializers.CharField(
        source="customer.full_name", read_only=True, default=None
    )
    merchant_id   = serializers.IntegerField(source="merchant.id",         read_only=True)

    # Display helpers for redemption orders — null for regular orders
    reward_name = serializers.CharField(
        source="reward_redemption.reward.name", read_only=True, default=None
    )
    punch_card_name = serializers.CharField(
        source="punch_card_redemption.punch_card.name", read_only=True, default=None
    )

    table_id = serializers.PrimaryKeyRelatedField(
        source="table", read_only=True, default=None
    )

    # POS-related read-only fields
    worker_name = serializers.CharField(
        source="processed_by_worker.display_name", read_only=True, default=None
    )

    class Meta:
        model = Order
        fields = [
            "id", "uuid",
            "customer", "customer_name",
            "merchant", "merchant_id", "merchant_name",
            "status", "order_type", "source", "fulfillment_type",
            "subtotal", "discount_type", "discount_value", "discount_amount",
            "tax_amount", "service_charge",
            "total_amount", "points_earned",
            "payment_status", "payment_method",
            "notes", "items",
            "cancellation_reason", "cancelled_by",
            "reward_name", "punch_card_name",
            "table_id", "table_name_snapshot", "table_number_snapshot",
            "processed_by_worker", "worker_name",
            "pos_device", "cash_shift",
            "version", "client_mutation_id", "client_created_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "uuid", "version", "created_at", "updated_at",
        ]


class CreateOrderItemSerializer(serializers.Serializer):
    menu_item_id = serializers.IntegerField()
    quantity     = serializers.IntegerField(min_value=1)


class CreateOrderSerializer(serializers.Serializer):
    merchant_id = serializers.IntegerField()
    items       = CreateOrderItemSerializer(many=True)
    notes       = serializers.CharField(required=False, allow_blank=True, default="")
    fulfillment_type = serializers.ChoiceField(
        choices=["dine_in", "pickup", "delivery"],
        default="pickup",
        required=False,
    )
    table_token = serializers.CharField(
        required=False, allow_blank=True, default="",
        help_text="Public token of the scanned table (required for dine-in)",
    )

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Order must contain at least one item.")
        return value
