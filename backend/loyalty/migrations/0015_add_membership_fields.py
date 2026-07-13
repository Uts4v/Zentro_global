"""
Add membership_number, last_active_at, is_active to CustomerMerchantProfile.

Phase 1: Add fields as nullable.
Phase 2: Backfill membership numbers for existing records.
Phase 3: Add unique constraint on membership_number.
"""

from django.db import migrations, models
import secrets


_SAFE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _generate_membership_number(slug: str) -> str:
    prefix_chars = [c for c in slug if c.isalpha()]
    prefix = "".join(prefix_chars[:3]).upper()
    prefix = prefix.ljust(3, "X")
    random_part = "".join(
        secrets.choice(_SAFE_ALPHABET) for _ in range(6)
    )
    return f"{prefix}-{random_part}"


def backfill_membership_numbers(apps, schema_editor):
    """Generate unique membership numbers for all existing profiles."""
    CustomerMerchantProfile = apps.get_model("loyalty", "CustomerMerchantProfile")
    MerchantProfile = apps.get_model("merchants", "MerchantProfile")

    used_numbers = set(
        CustomerMerchantProfile.objects.exclude(
            membership_number__isnull=True
        ).values_list("membership_number", flat=True)
    )

    for profile in CustomerMerchantProfile.objects.select_related("merchant").all():
        if profile.membership_number:
            continue
        merchant = profile.merchant
        for _ in range(100):
            candidate = _generate_membership_number(merchant.slug)
            if candidate not in used_numbers:
                used_numbers.add(candidate)
                profile.membership_number = candidate
                profile.save(update_fields=["membership_number"])
                break
        else:
            # Extremely unlikely fallback
            candidate = f"{merchant.slug[:3].upper()}-{secrets.token_hex(3).upper()}"
            while candidate in used_numbers:
                candidate = f"{merchant.slug[:3].upper()}-{secrets.token_hex(3).upper()}"
            used_numbers.add(candidate)
            profile.membership_number = candidate
            profile.save(update_fields=["membership_number"])


def reverse_backfill(apps, schema_editor):
    """No-op reverse — we keep generated numbers."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("loyalty", "0014_fix_stamp_gif_url_nullable"),
        ("merchants", "0001_initial"),
    ]

    operations = [
        # Phase1: Add new columns as nullable
        migrations.AddField(
            model_name="customermerchantprofile",
            name="membership_number",
            field=models.CharField(
                max_length=20,
                unique=True,
                blank=True,
                null=True,
                db_index=True,
                help_text="Unique merchant-specific membership ID, e.g. CAF-A91K22",
            ),
        ),
        migrations.AddField(
            model_name="customermerchantprofile",
            name="last_active_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="customermerchantprofile",
            name="is_active",
            field=models.BooleanField(default=True, db_index=True),
        ),
        # Phase 2: Backfill membership numbers
        migrations.RunPython(
            backfill_membership_numbers,
            reverse_backfill,
        ),
    ]
