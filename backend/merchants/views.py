# merchants/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import MerchantProfile, MenuItem
from .serializers import MerchantProfileSerializer, MerchantPublicSerializer, MenuItemSerializer
import re


def _get_or_create_merchant_profile(user) -> MerchantProfile:
    """Get or create a MerchantProfile for the given user, using store_name from metadata."""
    try:
        return user.merchant_profile
    except MerchantProfile.DoesNotExist:
        pass

    # Try to get store_name from user metadata (set during Supabase sign-up)
    store_name = ""
    try:
        # Access the Supabase user metadata via the JWT payload stored on the user
        # The user's role field tells us if they're a merchant
        if hasattr(user, "supabase_id"):
            # We can't access raw metadata here, so use email/username as fallback
            store_name = user.email.split("@")[0].title() if user.email else user.username.title()
        else:
            store_name = user.username.title() if user.username else "My Store"
    except Exception:
        store_name = "My Store"

    # Generate a unique slug
    base_slug = re.sub(r"[^a-z0-9]+", "-", store_name.lower())
    slug = base_slug
    counter = 1
    while MerchantProfile.objects.filter(store_slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return MerchantProfile.objects.create(
        user=user,
        store_name=store_name or "My Store",
        store_slug=slug,
    )


class MerchantViewSet(viewsets.ModelViewSet):
    """ViewSet for merchant profile management."""

    queryset = MerchantProfile.objects.all()
    serializer_class = MerchantProfileSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return MerchantProfile.objects.prefetch_related("menu_items").all()

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get the authenticated merchant's own profile (auto-creates if missing)."""
        profile = _get_or_create_merchant_profile(request.user)
        serializer = MerchantProfileSerializer(profile)
        return Response(serializer.data)

    @action(detail=False, methods=["patch"], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """Update the authenticated merchant's profile."""
        profile = _get_or_create_merchant_profile(request.user)
        serializer = MerchantProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def menu(self, request, pk=None):
        """Get a merchant's menu items (public)."""
        merchant = self.get_object()
        items = merchant.menu_items.filter(is_available=True)
        serializer = MenuItemSerializer(items, many=True)
        return Response(serializer.data)


class MenuItemViewSet(viewsets.ModelViewSet):
    """ViewSet for merchant menu item management."""

    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "my_items"]:
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        # Merchants see only their own items; customers see all available items
        if self.request.user.is_authenticated and hasattr(self.request.user, "merchant_profile"):
            return MenuItem.objects.filter(merchant=self.request.user.merchant_profile)
        return MenuItem.objects.filter(is_available=True)

    def perform_create(self, serializer):
        """Attach the authenticated merchant's profile on create."""
        merchant = _get_or_create_merchant_profile(self.request.user)
        serializer.save(merchant=merchant)

    def perform_update(self, serializer):
        """Ensure merchants can only update their own items."""
        instance = self.get_object()
        merchant = _get_or_create_merchant_profile(self.request.user)
        if instance.merchant != merchant:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only edit your own menu items.")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """Ensure merchants can only delete their own items."""
        instance = self.get_object()
        merchant = _get_or_create_merchant_profile(request.user)
        if instance.merchant != merchant:
            return Response({"error": "Not your item."}, status=status.HTTP_403_FORBIDDEN)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def my_items(self, request):
        """Get all menu items for the authenticated merchant (auto-creates profile if missing)."""
        merchant = _get_or_create_merchant_profile(request.user)
        items = MenuItem.objects.filter(merchant=merchant).order_by("category", "name")
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated])
    def toggle_availability(self, request, pk=None):
        """Toggle is_available on a menu item."""
        item = self.get_object()
        merchant = _get_or_create_merchant_profile(request.user)
        if item.merchant != merchant:
            return Response({"error": "Not your item."}, status=status.HTTP_403_FORBIDDEN)
        item.is_available = not item.is_available
        item.save()
        return Response(MenuItemSerializer(item).data)