"""
accounts/models.py

User and profile models.

- User: extends AbstractUser, adds role (customer | merchant) + avatar
- CustomerProfile: loyalty points, tier, streak, total orders
"""

from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Extended user model. role determines whether the user sees the
    customer dashboard or the merchant dashboard on the frontend.
    """

    ROLE_CUSTOMER = "customer"
    ROLE_MERCHANT = "merchant"
    ROLE_CHOICES = [
        (ROLE_CUSTOMER, "Customer"),
        (ROLE_MERCHANT, "Merchant"),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_CUSTOMER,
        db_index=True,
    )
    phone = models.CharField(max_length=20, blank=True)
    avatar_url = models.URLField(blank=True)

    # email is required and used for login (in addition to username)
    email = models.EmailField(unique=True)

    # Keep supabase_id for optional legacy compatibility; not used in new flows
    supabase_id = models.CharField(max_length=255, unique=True, null=True, blank=True)

    REQUIRED_FIELDS = []  # email is already USERNAME_FIELD by default via AbstractUser

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email or self.username

    @property
    def is_merchant(self) -> bool:
        return self.role == self.ROLE_MERCHANT

    @property
    def is_customer(self) -> bool:
        return self.role == self.ROLE_CUSTOMER


class CustomerProfile(models.Model):
    """
    Customer-specific loyalty data. Created automatically via signal
    whenever a new User with role='customer' is saved.
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

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    full_name = models.CharField(max_length=255, blank=True)
    loyalty_points = models.IntegerField(default=0)
    streak_days = models.IntegerField(default=0)
    last_order_date = models.DateField(null=True, blank=True)
    total_orders = models.IntegerField(default=0)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default=TIER_BRONZE)
    transfer_code = models.CharField(max_length=8, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customer_profiles"

    def __str__(self):
        return f"Customer: {self.full_name or self.user.email}"

    def save(self, *args, **kwargs):
        if not self.transfer_code:
            self.transfer_code = self._generate_transfer_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_transfer_code() -> str:
        import secrets
        import string
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(6))
            if not CustomerProfile.objects.filter(transfer_code=code).exists():
                return code

    def recalculate_tier(self):
        """
        Upgrade tier based on total lifetime points.
        Call this after awarding points.
        """
        pts = self.loyalty_points
        if pts >= 5000:
            tier = self.TIER_PLATINUM
        elif pts >= 2000:
            tier = self.TIER_GOLD
        elif pts >= 500:
            tier = self.TIER_SILVER
        else:
            tier = self.TIER_BRONZE

        if self.tier != tier:
            self.tier = tier
            self.save(update_fields=["tier"])

    def award_points(self, pts: int):
        """Add points and recalculate tier in one call."""
        self.loyalty_points = max(0, self.loyalty_points + pts)
        self.save(update_fields=["loyalty_points"])
        self.recalculate_tier()

    def deduct_points(self, pts: int):
        """Deduct points — raises ValueError if insufficient balance."""
        if self.loyalty_points < pts:
            raise ValueError(
                f"Insufficient points: have {self.loyalty_points}, need {pts}"
            )
        self.loyalty_points -= pts
        self.save(update_fields=["loyalty_points"])


class PasswordResetToken(models.Model):
    """
    Stores single-use password reset tokens.
    Expires after 1 hour (enforced in view).
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reset_tokens")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    class Meta:
        db_table = "password_reset_tokens"

    def __str__(self):
        return f"Reset token for {self.user.email}"
