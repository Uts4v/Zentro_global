from django.db import models
from django.conf import settings

# ── Add this to loyalty/models.py ────────────────────────────────────────────
# Place it after your existing Redemption model.

class PunchCard(models.Model):
    """
    Tracks a customer's punch card progress at a specific merchant.
    Every completed order = 1 punch. Every 5 punches = 1 free reward unlocked.
    Resets punch_count to 0 (and increments lifetime_punches) after each free reward.
    """

    customer = models.ForeignKey(
        "accounts.CustomerProfile",
        on_delete=models.CASCADE,
        related_name="punch_cards",
    )
    merchant = models.ForeignKey(
        "merchants.MerchantProfile",
        on_delete=models.CASCADE,
        related_name="punch_cards",
    )
    punch_count = models.IntegerField(default=0)          # current cycle (0–4)
    punches_to_free = models.IntegerField(default=5)      # merchant can configure this later
    lifetime_punches = models.IntegerField(default=0)     # total punches ever earned
    free_reward_available = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "punch_cards"
        unique_together = ["customer", "merchant"]

    def __str__(self):
        return f"{self.customer} @ {self.merchant} — {self.punch_count}/{self.punches_to_free}"

    def add_punch(self):
        """Award one punch. Returns True if this punch completed a free reward cycle."""
        self.punch_count += 1
        self.lifetime_punches += 1
        completed = False
        if self.punch_count >= self.punches_to_free:
            self.punch_count = 0
            self.free_reward_available = True
            completed = True
        self.save()
        return completed

    def use_free_reward(self):
        """Mark the free reward as used."""
        self.free_reward_available = False
        self.save()
class Mission(models.Model):
    """Loyalty missions/challenges for customers."""

    MISSION_TYPES = [
        ("purchase", "Purchase"),
        ("visit", "Visit"),
        ("referral", "Referral"),
        ("special", "Special"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    mission_type = models.CharField(max_length=20, choices=MISSION_TYPES, default="purchase")
    points_reward = models.IntegerField(default=10)
    required_count = models.IntegerField(default=1)
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
    """Tracks customer progress on missions."""

    customer = models.ForeignKey(
        "accounts.CustomerProfile",
        on_delete=models.CASCADE,
        related_name="missions",
    )
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE)
    progress = models.IntegerField(default=0)
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
    """Available rewards that customers can redeem."""

    merchant = models.ForeignKey(
        "merchants.MerchantProfile",
        on_delete=models.CASCADE,
        related_name="rewards",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
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


class Redemption(models.Model):
    """Tracks reward redemptions."""

    customer = models.ForeignKey(
        "accounts.CustomerProfile",
        on_delete=models.CASCADE,
        related_name="redemptions",
    )
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE)
    points_spent = models.IntegerField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("redeemed", "Redeemed"),
            ("expired", "Expired"),
            ("cancelled", "Cancelled"),
        ],
        default="pending",
    )
    code = models.CharField(max_length=50, unique=True)
    redeemed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "redemptions"

    def __str__(self):
        return f"{self.customer} - {self.reward.name}"
