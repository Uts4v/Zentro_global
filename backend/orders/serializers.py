# orders/serializers.py
from rest_framework import serializers
from .models import Order, OrderItem
from merchants.serializers import MenuItemSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "menu_item", "name", "price", "quantity", "subtotal"]
        read_only_fields = ["id"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    merchant_name = serializers.CharField(source="merchant.store_name", read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "customer", "customer_name", "merchant", "merchant_name",
            "status", "total_amount", "points_earned", "notes",
            "items", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CreateOrderSerializer(serializers.Serializer):
    merchant_id = serializers.IntegerField()
    items = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField())
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Order must have at least one item")
        for item in value:
            if "menu_item_id" not in item or "quantity" not in item:
                raise serializers.ValidationError(
                    "Each item must have menu_item_id and quantity"
                )
        return value