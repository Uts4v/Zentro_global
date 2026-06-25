# orders/signals.py
# ─────────────────────────────────────────────────────────────────────────────
# Wire this up by adding to orders/apps.py:
#
#   class OrdersConfig(AppConfig):
#       default_auto_field = "django.db.models.BigAutoField"
#       name = "orders"
#
#       def ready(self):
#           import orders.signals  # noqa: F401
#
# ─────────────────────────────────────────────────────────────────────────────

from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Order


@receiver(pre_save, sender=Order)
def award_punch_on_completion(sender, instance, **kwargs):
    """
    When an order transitions TO 'completed', award one punch on the customer's
    punch card for this merchant. If that completes a cycle, flag a free reward.
    """
    if not instance.pk:
        return  # brand-new order, skip

    try:
        previous = Order.objects.get(pk=instance.pk)
    except Order.DoesNotExist:
        return

    # Only fire when status changes TO completed (not on every save)
    if previous.status == instance.status:
        return
    if instance.status != "completed":
        return

    # Import here to avoid circular imports
    from loyalty.models import PunchCard

    punch_card, _ = PunchCard.objects.get_or_create(
        customer=instance.customer,
        merchant=instance.merchant,
        defaults={"punches_to_free": 5},
    )
    completed_cycle = punch_card.add_punch()

    # Optional: also award bonus loyalty points on cycle completion
    if completed_cycle:
        customer = instance.customer
        customer.loyalty_points = (customer.loyalty_points or 0) + 50  # 50 pt bonus
        customer.save(update_fields=["loyalty_points"])