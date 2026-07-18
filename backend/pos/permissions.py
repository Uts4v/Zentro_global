from rest_framework.permissions import BasePermission

from .models import _hash_token, PosDevice


class IsMerchantUser(BasePermission):
    """Ensure the authenticated user has a merchant profile."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "merchant_profile")
        )


class IsPosDevice(BasePermission):
    """Authenticate POS requests via device token header (no JWT required).

    Header: X-Pos-Device-Id: <uuid>
            X-Pos-Device-Token: <raw token>

    Sets ``request.pos_device`` and ``request.pos_merchant`` on success.
    """

    def has_permission(self, request, view):
        device_id = request.headers.get("X-Pos-Device-Id", "")
        device_token = request.headers.get("X-Pos-Device-Token", "")
        if not device_id or not device_token:
            return False
        try:
            device = PosDevice.objects.select_related("merchant").get(
                id=device_id,
                is_active=True,
            )
        except (PosDevice.DoesNotExist, Exception):
            return False
        if not device.verify_token(device_token):
            return False
        if not device.merchant.pos_enabled:
            return False
        device.last_seen_at = __import__("django.utils.timezone", fromlist=["now"]).now()
        device.save(update_fields=["last_seen_at", "updated_at"])
        request.pos_device = device
        request.pos_merchant = device.merchant
        return True


class IsPosEnabled(BasePermission):
    """Ensure the merchant has POS enabled."""

    def has_permission(self, request, view):
        if not hasattr(request.user, "merchant_profile"):
            return False
        return request.user.merchant_profile.pos_enabled


class IsMerchantOwner(BasePermission):
    """Object-level: ensure the object belongs to the merchant."""

    def has_object_permission(self, request, view, obj):
        merchant = request.user.merchant_profile
        if hasattr(obj, "merchant"):
            return obj.merchant == merchant
        return False


class HasWorkerPermission(BasePermission):
    """Ensure the worker session belongs to the same merchant."""

    def has_permission(self, request, view):
        merchant = request.user.merchant_profile
        worker = getattr(request, "worker", None)
        if worker is None:
            return False
        return worker.merchant == merchant and worker.is_active


class CanApplyDiscount(BasePermission):
    """Ensure the worker has discount permission."""

    def has_permission(self, request, view):
        worker = getattr(request, "worker", None)
        if worker is None:
            return False
        return worker.can_apply_discount


class CanProcessRefund(BasePermission):
    """Ensure the worker has refund permission."""

    def has_permission(self, request, view):
        worker = getattr(request, "worker", None)
        if worker is None:
            return False
        return worker.can_process_refund


class CanCloseShift(BasePermission):
    """Ensure the worker has shift-close permission."""

    def has_permission(self, request, view):
        worker = getattr(request, "worker", None)
        if worker is None:
            return False
        return worker.can_close_shift


class CanViewReports(BasePermission):
    """Ensure the worker has report-viewing permission."""

    def has_permission(self, request, view):
        worker = getattr(request, "worker", None)
        if worker is None:
            return False
        return worker.can_view_reports
