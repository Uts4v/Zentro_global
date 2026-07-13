# merchants/models.py
import secrets
from django.db import models
from django.conf import settings


def _generate_table_token():
    return f"TBL-{secrets.token_urlsafe(8)}".upper()


class MerchantProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="merchant_profile",
    )

    # Renamed: store_name → business_name, store_slug → slug
    # db_column keeps the existing DB column so no data is lost
    business_name = models.CharField(max_length=255, db_column="store_name")
    slug = models.SlugField(unique=True, db_column="store_slug")

    business_type = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    logo_url = models.URLField(blank=True)
    banner_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    is_open = models.BooleanField(default=True)

    # New fields
    onboarding_complete = models.BooleanField(default=False)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    qr_code = models.TextField(blank=True)  # stores the public URL or SVG string

    store_theme_color = models.CharField(max_length=7, blank=True, default="", help_text="Hex color for customer store view, e.g. #1e293b")

    # Table ordering settings
    table_ordering_enabled = models.BooleanField(
        default=False,
        help_text="Enable table-based ordering for dine-in customers",
    )
    allow_pickup = models.BooleanField(default=True)
    allow_delivery = models.BooleanField(default=False)
    allow_dine_in = models.BooleanField(default=False)
    allow_point_transfer = models.BooleanField(
        default=False,
        help_text="Allow customers to transfer points to other members of this business",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "merchant_profiles"

    def __str__(self):
        return self.business_name


class MenuItem(models.Model):
    merchant = models.ForeignKey(
        MerchantProfile,
        on_delete=models.CASCADE,
        related_name="menu_items",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    loyalty_reward = models.BooleanField(default=True)
    points_per_item = models.IntegerField(default=1)
    emoji = models.CharField(max_length=10, default="☕")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "menu_items"
        ordering = ["category", "name"]

    def __str__(self):
        # updated to use new field name
        return f"{self.name} - {self.merchant.business_name}"


class MerchantTable(models.Model):
    merchant = models.ForeignKey(
        MerchantProfile,
        on_delete=models.CASCADE,
        related_name="tables",
    )
    name = models.CharField(
        max_length=100,
        help_text="User-facing label, e.g. 'Table 4', 'Patio A', 'VIP Lounge'",
    )
    table_number = models.PositiveIntegerField(
        help_text="Numeric ordering label for sorting",
    )
    public_token = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        default=_generate_table_token,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "merchant_tables"
        constraints = [
            models.UniqueConstraint(
                fields=["merchant", "table_number"],
                name="unique_table_number_per_merchant",
            ),
        ]
        ordering = ["table_number"]

    def __str__(self):
        return f"{self.name} ({self.merchant.business_name})"

    def regenerate_token(self):
        self.public_token = _generate_table_token()
        self.save(update_fields=["public_token", "updated_at"])