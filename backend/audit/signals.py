"""
audit/signals.py

Auto-log security-sensitive events from Django signals / post-save hooks.
This module is imported in AuditConfig.ready() so signal handlers are registered
at app startup.
"""

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AuditLog


@receiver(user_logged_in)
def _on_login(sender, request, user, **kwargs):
    AuditLog.log(
        AuditLog.ACTION_LOGIN,
        request=request,
        user=user,
        details={"method": "jwt"},
    )


@receiver(user_login_failed)
def _on_login_failed(sender, credentials, request, **kwargs):
    AuditLog.log(
        AuditLog.ACTION_LOGIN_FAILED,
        request=request,
        details={"email": credentials.get("email", "")},
    )


@receiver(post_save, sender="accounts.User")
def _on_user_created(sender, instance, created, **kwargs):
    if created:
        AuditLog.log(
            AuditLog.ACTION_REGISTER,
            user=instance,
            details={"email": instance.email, "role": instance.role},
        )
