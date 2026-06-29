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
    list_display = ["id", "customer", "merchant", "status", "total_amount", "points_earned", "created_at"]
    list_filter = ["status"]
    search_fields = ["customer__full_name", "merchant__store_name"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"
