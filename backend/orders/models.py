# orders/models.py
from django.db import models


class Order(models.Model):
    STATUS_PENDING   = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_PREPARING = "preparing"
    STATUS_READY     = "ready"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING,   "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_PREPARING, "Preparing"),
        (STATUS_READY,     "Ready"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    ORDER_TYPE_REGULAR         = "regular"
    ORDER_TYPE_PUNCH_REDEMPTION = "punch_card_redemption"
    ORDER_TYPE_REWARD_REDEMPTION = "reward_redemption"

    ORDER_TYPE_CHOICES = [
        (ORDER_TYPE_REGULAR,           "Regular"),
        (ORDER_TYPE_PUNCH_REDEMPTION,  "Punch Card Redemption"),
        (ORDER_TYPE_REWARD_REDEMPTION, "Reward Redemption"),
    ]

    CANCEL_REASON_CUSTOMER_REQUEST = "customer_request"
    CANCEL_REASON_OUT_OF_STOCK     = "out_of_stock"
    CANCEL_REASON_STORE_CLOSING    = "store_closing"
    CANCEL_REASON_OTHER            = "other"

    CANCEL_REASON_CHOICES = [
        (CANCEL_REASON_CUSTOMER_REQUEST, "Customer Request"),
        (CANCEL_REASON_OUT_OF_STOCK,     "Out of Stock"),
        (CANCEL_REASON_STORE_CLOSING,    "Store Closing"),
        (CANCEL_REASON_OTHER,            "Other"),
    ]

    CANCELLED_BY_CUSTOMER = "customer"
    CANCELLED_BY_MERCHANT = "merchant"

    customer = models.ForeignKey(
        "accounts.CustomerProfile",
        on_delete=models.CASCADE,
        related_name="orders",
    )
    merchant = models.ForeignKey(
        "merchants.MerchantProfile",
        on_delete=models.CASCADE,
        related_name="orders",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_PENDING, db_index=True,
    )
    order_type = models.CharField(
        max_length=30, choices=ORDER_TYPE_CHOICES,
        default=ORDER_TYPE_REGULAR,
        db_index=True,
    )
    total_amount    = models.DecimalField(max_digits=10, decimal_places=2)
    points_earned   = models.IntegerField(default=0)
    loyalty_awarded = models.BooleanField(default=False)
    notes           = models.TextField(blank=True)

    # Cancellation
    cancellation_reason = models.CharField(
        max_length=50, choices=CANCEL_REASON_CHOICES,
        blank=True, default="",
    )
    cancelled_by = models.CharField(max_length=20, blank=True, default="")

    # For punch card redemption orders — link back to the card
    punch_card_redemption = models.ForeignKey(
        "loyalty.CustomerPunchCard",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="redemption_orders",
    )

    # For reward redemption orders — link back to the redemption record,
    # mirrors punch_card_redemption above.
    reward_redemption = models.ForeignKey(
        "loyalty.Redemption",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="order",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} [{self.status}] — {self.customer}"


class OrderItem(models.Model):
    order     = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(
        "merchants.MenuItem",
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    name     = models.CharField(max_length=255)
    price    = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=1)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "order_items"

    def __str__(self):
        return f"{self.quantity}× {self.name}"