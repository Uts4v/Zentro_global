"""
audit/models.py

Immutable audit log for security-sensitive operations.

Captures:
  - reward approval / confirmation
  - point manual adjustment
  - point transfer
  - order completion
  - login (success/failure)
  - registration
  - password change/reset
"""

from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    ACTION_LOGIN = "login"
    ACTION_LOGIN_FAILED = "login_failed"
    ACTION_REGISTER = "register"
    ACTION_PASSWORD_CHANGE = "password_change"
    ACTION_PASSWORD_RESET = "password_reset"
    ACTION_REWARD_CONFIRMED = "reward_confirmed"
    ACTION_PUNCH_CARD_CONFIRMED = "punch_card_confirmed"
    ACTION_POINT_ADJUSTMENT = "point_adjustment"
    ACTION_POINT_TRANSFER = "point_transfer"
    ACTION_ORDER_COMPLETED = "order_completed"
    ACTION_ORDER_CANCELLED = "order_cancelled"
    ACTION_REWARD_REDEEMED = "reward_redeemed"

    ACTION_CHOICES = [
        (ACTION_LOGIN, "Login"),
        (ACTION_LOGIN_FAILED, "Login Failed"),
        (ACTION_REGISTER, "Register"),
        (ACTION_PASSWORD_CHANGE, "Password Change"),
        (ACTION_PASSWORD_RESET, "Password Reset"),
        (ACTION_REWARD_CONFIRMED, "Reward Confirmed"),
        (ACTION_PUNCH_CARD_CONFIRMED, "Punch Card Confirmed"),
        (ACTION_POINT_ADJUSTMENT, "Point Adjustment"),
        (ACTION_POINT_TRANSFER, "Point Transfer"),
        (ACTION_ORDER_COMPLETED, "Order Completed"),
        (ACTION_ORDER_CANCELLED, "Order Cancelled"),
        (ACTION_REWARD_REDEEMED, "Reward Redeemed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    target_model = models.CharField(max_length=100, blank=True, default="")
    target_id = models.CharField(max_length=50, blank=True, default="")
    merchant = models.ForeignKey(
        "merchants.MerchantProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, default="")
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["merchant", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.action}] user={self.user_id} target={self.target_model}:{self.target_id} @ {self.created_at}"

    @classmethod
    def log(cls, action, request=None, user=None, merchant=None, target_model="",
            target_id="", details=None):
        """
        Convenience factory — call from anywhere:
            AuditLog.log(AuditLog.ACTION_ORDER_COMPLETED, request=request, ...)
        """
        ip = ""
        ua = ""
        if request:
            ip = _get_client_ip(request)
            ua = request.META.get("HTTP_USER_AGENT", "")[:500]
            if user is None:
                user = getattr(request, "user", None)
                if user and not user.is_authenticated:
                    user = None

        return cls.objects.create(
            user=user,
            action=action,
            target_model=target_model,
            target_id=str(target_id),
            merchant=merchant,
            ip_address=ip or None,
            user_agent=ua,
            details=details or {},
        )


def _get_client_ip(request):
    """Extract client IP considering X-Forwarded-For (reverse proxy)."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
