"""
loyalty/models.py

All loyalty-related models:
  - PunchCard       : per-customer, per-merchant punch tracking
  - LoyaltyRules    : per-merchant configurable loyalty rules
  - Mission         : challenges/goals merchants create
  - CustomerMission : tracks customer progress on a mission
  - Reward          : redeemable rewards merchants create
  - Redemption      : records of reward redemptions by customers
"""

from django.db import models
class TodaySpecial(models.Model):
    merchant = models.ForeignKey(
        "merchants.MerchantProfile",
        on_delete=models.CASCADE,
        related_name="today_specials",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    linked_menu_item = models.ForeignKey(
        "merchants.MenuItem",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="specials",
    )
    linked_reward = models.ForeignKey(
        "loyalty.Reward",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="specials",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "today_specials"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.merchant.business_name}"

class CustomerMerchantProfile(models.Model):
    """
    Links a customer to a merchant after QR scan / slug onboarding.
    """

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    customer = models.ForeignKey(
        "accounts.CustomerProfile",
        on_delete=models.CASCADE,
        related_name="merchant_profiles",
    )
    merchant = models.ForeignKey(
        "merchants.MerchantProfile",
        on_delete=models.CASCADE,
        related_name="customer_profiles",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customer_merchant_profiles"
        unique_together = ["customer", "merchant"]

    def __str__(self):
        return f"{self.customer} @ {self.merchant}"


class CustomerMerchantWallet(models.Model):
    """
    Per-merchant point wallet. Points are never shared across merchants.
    """

    TIER_BRONZE = "bronze"
    TIER_SILVER = "silver"
    TIER_GOLD = "gold"
    TIER_PLATINUM = "platinum"
    TIER_CHOICES = [
        (TIER_BRONZE, "Bronze"),
        (TIER_SILVER, "Silver"),
        (TIER_GOLD, "Gold"),
        (TIER_PLATINUM, "Platinum"),
    ]

    customer = models.ForeignKey(
        "accounts.CustomerProfile",
        on_delete=models.CASCADE,
        related_name="merchant_wallets",
    )
    merchant = models.ForeignKey(
        "merchants.MerchantProfile",
        on_delete=models.CASCADE,
        related_name="customer_wallets",
    )
    points_balance = models.IntegerField(default=0)
    lifetime_points = models.IntegerField(default=0)
    expired_points = models.IntegerField(default=0)
    order_count = models.IntegerField(default=0)
    streak_days = models.IntegerField(default=0)
    last_order_datetime = models.DateTimeField(null=True, blank=True)
    last_point_earned_at = models.DateTimeField(null=True, blank=True)
    tier_level = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        default=TIER_BRONZE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customer_merchant_wallets"
        unique_together = ["customer", "merchant"]
        indexes = [
            models.Index(fields=["merchant", "-points_balance"]),
        ]

    def __str__(self):
        return f"{self.customer} @ {self.merchant} — {self.points_balance} pts"


class LoyaltyRules(models.Model):
    """
    Per-merchant loyalty configuration.
    Auto-created with sensible defaults when a merchant requests their rules.
    """

    merchant = models.OneToOneField(
        "merchants.MerchantProfile",
        on_delete=models.CASCADE,
        related_name="loyalty_rules",
    )
    # Points awarded per unit of currency (e.g., 1 point per NPR 1 spent)
    points_per_npr = models.FloatField(default=1.0)
    # Multiplier applied to points when a streak is active
    streak_multiplier = models.FloatField(default=1.5)
    # Bonus points awarded on first order (welcome bonus)
    welcome_bonus = models.IntegerField(default=50)
    # Bonus points awarded on customer birthday
    birthday_bonus = models.IntegerField(default=100)
    # Minimum order amount (in NPR) required to increment the streak
    streak_min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "loyalty_rules"

    def __str__(self):
        return f"Rules for {self.merchant.business_name}"


class MerchantPunchCard(models.Model):
    """
    Merchant's configuration for a punch card.
    """
    MODE_PER_ORDER = "per_order"
    MODE_PER_STREAK = "per_streak"
    MODE_CHOICES = [
        (MODE_PER_ORDER, "Per Order"),
        (MODE_PER_STREAK, "Per Streak"),
    ]

    merchant = models.ForeignKey(
        "merchants.MerchantProfile",
        on_delete=models.CASCADE,
        related_name="punch_cards",
    )
    name = models.CharField(max_length=255)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default=MODE_PER_ORDER)
    stamps_required = models.IntegerField(default=5)
    reward_text = models.CharField(max_length=255, help_text="Text description of the reward (e.g., 'Free Coffee')")
    
    # Customization
    background_image = models.URLField(blank=True)
    animated_gif_background = models.URLField(blank=True)
    color_scheme = models.CharField(max_length=20, default="#FFFFFF", help_text="Hex color code")
    stamp_icon = models.CharField(max_length=255, default="☕", help_text="Emoji or URL to stamp icon")
    logo = models.URLField(blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "merchant_punch_cards"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.merchant}"


class CustomerPunchCard(models.Model):
    """
    Tracks a customer's progress on a specific MerchantPunchCard.
    """
    customer = models.ForeignKey(
        "accounts.CustomerProfile",
        on_delete=models.CASCADE,
        related_name="punch_cards",
    )
    punch_card = models.ForeignKey(
        MerchantPunchCard,
        on_delete=models.CASCADE,
        related_name="customer_progress",
    )
    merchant = models.ForeignKey(
        "merchants.MerchantProfile",
        on_delete=models.CASCADE,
        related_name="customer_punch_cards",
    )
    current_stamps = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_redeemed = models.BooleanField(default=False)
    redeemed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customer_punch_cards"
        unique_together = ["customer", "punch_card", "is_completed"] # Can only have one active card of the same type at a time. Once completed, they can start a new one.

    def __str__(self):
        return f"{self.customer} - {self.punch_card.name}: {self.current_stamps}/{self.punch_card.stamps_required}"

    def add_punch(self) -> bool:
        """
        Award one punch. Returns True if this punch completed the card.
        """
        if self.is_completed:
            return False
            
        self.current_stamps += 1
        completed = False
        if self.current_stamps >= self.punch_card.stamps_required:
            self.is_completed = True
            from django.utils import timezone
            self.completed_at = timezone.now()
            completed = True
        self.save()
        return completed
        
    def redeem(self):
        if not self.is_completed:
            raise ValueError("Card is not completed yet.")
        if self.is_redeemed:
            raise ValueError("Card is already redeemed.")
        
        self.is_redeemed = True
        from django.utils import timezone
        self.redeemed_at = timezone.now()
        self.save(update_fields=["is_redeemed", "redeemed_at", "updated_at"])


class PointTransaction(models.Model):
    """
    Ledger for all point changes. Points should never be modified without a transaction.
    """
    TRANSACTION_TYPES = [
        ("EARNED", "Earned"),
        ("REDEEMED", "Redeemed"),
        ("MISSION_BONUS", "Mission Bonus"),
        ("PUNCH_CARD_REWARD", "Punch Card Reward"),
        ("EXPIRED", "Expired"),
        ("MANUAL_ADJUSTMENT", "Manual Adjustment"),
        ("TRANSFER_SENT", "Transfer Sent"),
        ("TRANSFER_RECEIVED", "Transfer Received"),
    ]

    merchant = models.ForeignKey("merchants.MerchantProfile", on_delete=models.CASCADE, related_name="point_transactions")
    customer = models.ForeignKey("accounts.CustomerProfile", on_delete=models.CASCADE, related_name="point_transactions")
    wallet = models.ForeignKey(CustomerMerchantWallet, on_delete=models.CASCADE, related_name="transactions")
    
    # Context references
    order = models.ForeignKey("orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="point_transactions")
    reward = models.ForeignKey("Reward", on_delete=models.SET_NULL, null=True, blank=True, related_name="point_transactions")
    mission = models.ForeignKey("Mission", on_delete=models.SET_NULL, null=True, blank=True, related_name="point_transactions")
    punch_card = models.ForeignKey(CustomerPunchCard, on_delete=models.SET_NULL, null=True, blank=True, related_name="point_transactions")
    
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES)
    points = models.IntegerField() # Positive for earned, negative for redeemed
    balance_before = models.IntegerField()
    balance_after = models.IntegerField()
    expiry_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="completed")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "point_transactions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction_type}: {self.points} pts for {self.customer} @ {self.merchant}"


class Mission(models.Model):
    """Loyalty missions / challenges that merchants create for their customers."""

    MISSION_TYPES = [
        ("order_count", "Order Count"),
        ("spend_amount", "Spend Amount"),
        ("visit_streak", "Visit Streak"),
        ("purchase", "Purchase"),
        ("visit", "Visit"),
        ("referral", "Referral"),
        ("special", "Special"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, default="🎯")
    mission_type = models.CharField(max_length=20, choices=MISSION_TYPES, default="order_count")
    target_count = models.IntegerField(default=1)
    reward_points = models.IntegerField(default=10)  # replaces points_reward for API parity
    required_merchant = models.ForeignKey(
        "merchants.MerchantProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="missions",
    )
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "missions"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class CustomerMission(models.Model):
    """Tracks a customer's progress on a specific mission."""

    customer = models.ForeignKey(
        "accounts.CustomerProfile",
        on_delete=models.CASCADE,
        related_name="missions",
    )
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="progress_entries")
    current_count = models.IntegerField(default=0)   # replaces `progress` for API parity
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customer_missions"
        unique_together = ["customer", "mission"]

    def __str__(self):
        return f"{self.customer} - {self.mission.title}"


class Reward(models.Model):
    """A redeemable reward that a merchant offers to customers."""

    merchant = models.ForeignKey(
        "merchants.MerchantProfile",
        on_delete=models.CASCADE,
        related_name="rewards",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    emoji = models.CharField(max_length=10, default="🎁")
    points_cost = models.IntegerField()
    image_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    stock = models.IntegerField(default=-1)  # -1 = unlimited
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rewards"
        ordering = ["points_cost"]

    def __str__(self):
        return f"{self.name} ({self.points_cost} pts)"

    @property
    def is_in_stock(self) -> bool:
        return self.stock == -1 or self.stock > 0


class Redemption(models.Model):
    """Records a customer redeeming a reward."""

    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    customer = models.ForeignKey(
        "accounts.CustomerProfile",
        on_delete=models.CASCADE,
        related_name="redemptions",
    )
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE, related_name="redemptions")
    points_spent = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "redemptions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer} — {self.reward.name} [{self.code}]"
