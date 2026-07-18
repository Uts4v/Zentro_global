# orders/models.py
import uuid

from django.db import models
from django.utils import timezone


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

    # Valid status transitions (source -> set of allowed targets)
    VALID_TRANSITIONS = {
        STATUS_PENDING:   {STATUS_CONFIRMED, STATUS_CANCELLED},
        STATUS_CONFIRMED: {STATUS_PREPARING, STATUS_CANCELLED, STATUS_READY},
        STATUS_PREPARING: {STATUS_READY, STATUS_CANCELLED},
        STATUS_READY:     {STATUS_COMPLETED, STATUS_CANCELLED},
        STATUS_COMPLETED: set(),
        STATUS_CANCELLED: set(),
    }

    ORDER_TYPE_REGULAR         = "regular"
    ORDER_TYPE_PUNCH_REDEMPTION = "punch_card_redemption"
    ORDER_TYPE_REWARD_REDEMPTION = "reward_redemption"

    ORDER_TYPE_CHOICES = [
        (ORDER_TYPE_REGULAR,           "Regular"),
        (ORDER_TYPE_PUNCH_REDEMPTION,  "Punch Card Redemption"),
        (ORDER_TYPE_REWARD_REDEMPTION, "Reward Redemption"),
    ]

    # Fulfillment type
    FULFILLMENT_DINE_IN  = "dine_in"
    FULFILLMENT_PICKUP   = "pickup"
    FULFILLMENT_DELIVERY = "delivery"

    FULFILLMENT_CHOICES = [
        (FULFILLMENT_DINE_IN,  "Dine In"),
        (FULFILLMENT_PICKUP,   "Pickup"),
        (FULFILLMENT_DELIVERY, "Delivery"),
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

    # Order source
    SOURCE_CUSTOMER_APP = "customer_app"
    SOURCE_TABLE_QR = "table_qr"
    SOURCE_MERCHANT_DASHBOARD = "merchant_dashboard"
    SOURCE_POS_ONLINE = "pos_online"
    SOURCE_POS_OFFLINE = "pos_offline"

    SOURCE_CHOICES = [
        (SOURCE_CUSTOMER_APP, "Customer App"),
        (SOURCE_TABLE_QR, "Table QR"),
        (SOURCE_MERCHANT_DASHBOARD, "Merchant Dashboard"),
        (SOURCE_POS_ONLINE, "POS Online"),
        (SOURCE_POS_OFFLINE, "POS Offline"),
    ]

    # UUID for client-facing identification (prevents local/server ID collisions)
    uuid = models.UUIDField(default=uuid.uuid4, db_index=True)

    # Nullable customer — walk-in POS orders have customer=null
    customer = models.ForeignKey(
        "accounts.CustomerProfile",
        on_delete=models.CASCADE,
        related_name="orders",
        null=True, blank=True,
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
    source = models.CharField(
        max_length=30, choices=SOURCE_CHOICES,
        default=SOURCE_CUSTOMER_APP,
        db_index=True,
    )
    fulfillment_type = models.CharField(
        max_length=20, choices=FULFILLMENT_CHOICES,
        default=FULFILLMENT_PICKUP,
        db_index=True,
    )

    # Totals (server-calculated)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_type = models.CharField(
        max_length=20, blank=True, default="",
        help_text="fixed or percentage",
    )
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Discount amount or percentage value",
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Calculated discount applied to subtotal",
    )
    tax_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
    )
    service_charge = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
    )
    total_amount    = models.DecimalField(max_digits=10, decimal_places=2)
    points_earned   = models.IntegerField(default=0)
    loyalty_awarded = models.BooleanField(default=False)
    is_reward_order = models.BooleanField(default=False)
    notes           = models.TextField(blank=True)

    # Table association (only for dine-in orders)
    table = models.ForeignKey(
        "merchants.MerchantTable",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="orders",
    )
    table_name_snapshot = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Preserved table name for historical reference",
    )
    table_number_snapshot = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Preserved table number for historical reference",
    )

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

    # ── POS fields ─────────────────────────────────────────────────────────────
    processed_by_worker = models.ForeignKey(
        "pos.ShiftWorker",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="orders",
        help_text="POS worker who processed this order",
    )
    pos_device = models.ForeignKey(
        "pos.PosDevice",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="orders",
        help_text="POS device that created this order",
    )
    cash_shift = models.ForeignKey(
        "pos.CashShift",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="orders",
        help_text="Cash shift during which this order was created",
    )
    payment_status = models.CharField(
        max_length=20, default="unpaid",
        help_text="unpaid, paid, partially_paid, refunded",
        db_index=True,
    )
    payment_method = models.CharField(
        max_length=30, blank=True, default="",
        help_text="Primary payment method for this order",
    )
    kot_number = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Kitchen Order Ticket number (sequential per merchant)",
    )

    # Optimistic concurrency and sync
    version = models.PositiveIntegerField(
        default=1,
        help_text="Increments on every update for conflict detection",
    )
    client_mutation_id = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="Idempotency key for offline sync",
    )
    client_created_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Client-side timestamp for offline orders",
    )
    sync_origin = models.CharField(
        max_length=20, blank=True, default="",
        help_text="Origin of the order for sync tracking",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        customer_label = self.customer or "Walk-in"
        return f"Order #{self.id} [{self.status}] — {customer_label}"

    def can_transition_to(self, new_status):
        """Check if a status transition is valid."""
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status):
        """
        Validate and perform a status transition.
        Raises ValueError if transition is invalid.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition from '{self.status}' to '{new_status}'. "
                f"Allowed: {', '.join(self.VALID_TRANSITIONS.get(self.status, set())) or 'none'}"
            )
        self.status = new_status
        self.version += 1


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