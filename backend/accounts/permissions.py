"""
accounts/permissions.py

Role-based permission classes for the Zentro Loyalty API.

Roles:
  - admin          : full system access (superuser/staff)
  - merchant_owner : owns a MerchantProfile, full merchant management
  - merchant_staff : works for a merchant (future: scoped access)
  - customer       : loyalty customer
"""

from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Allow only admin / staff users."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsMerchantOwner(BasePermission):
    """Allow only users with a MerchantProfile (role=merchant)."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_merchant
        )

    def has_object_permission(self, request, view, obj):
        if not self.has_permission(request, view):
            return False
        merchant = request.user.merchant_profile
        # Support obj.merchant (FK) or obj being the MerchantProfile itself
        if hasattr(obj, "merchant"):
            return obj.merchant_id == merchant.pk
        if hasattr(obj, "pk"):
            return obj.pk == merchant.pk
        return False


class IsMerchantStaff(BasePermission):
    """
    Allow merchant-role users. In a future expansion this can be scoped
    to specific merchant IDs stored on the user. For now it is equivalent
    to IsMerchantOwner but kept separate so the hierarchy is explicit.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_merchant
        )


class IsCustomer(BasePermission):
    """Allow only users with a CustomerProfile (role=customer)."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_customer
        )


class IsOwnerOrMerchantOrAdmin(BasePermission):
    """
    Object-level permission:
      - Customers can only access their own objects.
      - Merchants can access objects belonging to their merchant.
      - Admins can access anything.

    The object must expose either `customer` or `merchant` FK,
    or be checked against `request.user` directly.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False

        if user.is_staff:
            return True

        # Check if the object has a customer FK (order, transaction, etc.)
        if hasattr(obj, "customer_id"):
            if user.is_customer:
                return obj.customer_id == getattr(user, "customer_profile", None) and \
                       obj.customer_id == getattr(getattr(user, "customer_profile", None), "pk", None)
            if user.is_merchant:
                merchant = getattr(user, "merchant_profile", None)
                if merchant and hasattr(obj, "merchant_id"):
                    return obj.merchant_id == merchant.pk
                return False

        # Check if the object has a merchant FK (menu item, reward, etc.)
        if hasattr(obj, "merchant_id") and user.is_merchant:
            merchant = getattr(user, "merchant_profile", None)
            return merchant and obj.merchant_id == merchant.pk

        # Fallback: object belongs to the user directly
        if hasattr(obj, "user_id"):
            return obj.user_id == user.pk

        return False


class IsMerchantOwnerOrAdmin(BasePermission):
    """
    Object-level: merchant must own the object, or user is admin.
    Used for merchant resources like MerchantProfile, MenuItem, etc.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        return user.is_merchant

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff:
            return True
        if not user.is_merchant:
            return False

        merchant = getattr(user, "merchant_profile", None)
        if not merchant:
            return False

        if hasattr(obj, "merchant_id"):
            return obj.merchant_id == merchant.pk
        if hasattr(obj, "pk"):
            return obj.pk == merchant.pk
        return False


class IsCustomerOrMerchantOwner(BasePermission):
    """
    Object-level: customer accessing own data, or merchant accessing their own data.
    Used for shared resources like PointTransaction, Order.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_staff:
            return True

        if user.is_customer:
            cp = getattr(user, "customer_profile", None)
            if cp and hasattr(obj, "customer_id"):
                return obj.customer_id == cp.pk
            return False

        if user.is_merchant:
            mp = getattr(user, "merchant_profile", None)
            if mp and hasattr(obj, "merchant_id"):
                return obj.merchant_id == mp.pk
            return False

        return False
