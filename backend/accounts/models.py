from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Extended user model for Django admin and backend services."""

    supabase_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    role = models.CharField(
        max_length=20,
        choices=[("customer", "Customer"), ("merchant", "Merchant")],
        default="customer",
    )
    phone = models.CharField(max_length=20, blank=True)
    avatar_url = models.URLField(blank=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email or self.username


class CustomerProfile(models.Model):
    """Customer-specific profile data."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer_profile")
    full_name = models.CharField(max_length=255, blank=True)
    loyalty_points = models.IntegerField(default=0)
    streak_days = models.IntegerField(default=0)
    total_orders = models.IntegerField(default=0)
    tier = models.CharField(
        max_length=20,
        choices=[
            ("bronze", "Bronze"),
            ("silver", "Silver"),
            ("gold", "Gold"),
            ("platinum", "Platinum"),
        ],
        default="bronze",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customer_profiles"

    def __str__(self):
        return f"Customer: {self.full_name or self.user.email}"
