"""
orders/admin.py
"""

from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["subtotal"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display   = ["id", "customer", "merchant", "status", "order_type", "total_amount", "points_earned", "created_at"]
    list_filter    = ["status", "order_type"]
    search_fields  = ["customer__full_name", "merchant__business_name"]
    readonly_fields = ["created_at", "updated_at"]
    inlines        = [OrderItemInline]
    date_hierarchy = "created_at"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display  = ["id", "order", "name", "quantity", "price", "subtotal"]
    search_fields = ["name", "order__id"]