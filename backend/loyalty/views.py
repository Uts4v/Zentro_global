# loyalty/views.py
import os
import requests
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission

from accounts.models import CustomerProfile
from .models import Mission, CustomerMission, Reward, Redemption, PunchCard
from .serializers import (
    MissionSerializer,
    CustomerMissionSerializer,
    RewardSerializer,
    RedemptionSerializer,
    PunchCardSerializer,
)


class IsMerchant(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "merchant_profile")
        )


def get_or_create_customer(user):
    """Helper to get or create customer profile."""
    profile, _ = CustomerProfile.objects.get_or_create(
        user=user,
        defaults={
            "full_name": user.email or user.username,
            "loyalty_points": 0,
            "streak_days": 0,
            "total_orders": 0,
            "tier": "bronze",
        },
    )
    return profile


def sync_points_to_supabase(supabase_user_id: str, new_points: int):
    """
    Push updated loyalty points back to Supabase profiles table.
    Uses the Supabase service role key so it bypasses RLS.
    Call this after ANY points change in Django.
    """
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_role_key:
        # Env vars not set — log and skip (don't crash the request)
        print("[sync_points] WARNING: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        return

    url = f"{supabase_url}/rest/v1/profiles?id=eq.{supabase_user_id}"
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    try:
        resp = requests.patch(url, json={"points": new_points}, headers=headers, timeout=5)
        if resp.status_code not in (200, 204):
            print(f"[sync_points] Supabase update failed: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[sync_points] Request error: {e}")


# ── Missions ──────────────────────────────────────────────────────────────────

class MissionViewSet(viewsets.ModelViewSet):
    serializer_class = MissionSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "merchant_missions"]:
            return [IsAuthenticated(), IsMerchant()]
        if self.action in ["my_missions", "list", "retrieve"]:
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user
        # Merchants see only their own missions for edit/delete
        if (
            self.action in ["update", "partial_update", "destroy"]
            and user.is_authenticated
            and hasattr(user, "merchant_profile")
        ):
            return Mission.objects.filter(required_merchant=user.merchant_profile)
        # Default: all active missions (customers see these)
        return Mission.objects.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(required_merchant=self.request.user.merchant_profile)

    def perform_update(self, serializer):
        serializer.save(required_merchant=self.request.user.merchant_profile)

    @action(detail=False, methods=["get"])
    def active(self, request):
        missions = Mission.objects.filter(is_active=True)
        merchant_id = request.query_params.get("merchant")
        if merchant_id:
            missions = missions.filter(required_merchant_id=merchant_id)
        return Response(MissionSerializer(missions, many=True, context={"request": request}).data)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsMerchant])
    def merchant_missions(self, request):
        """
        Merchant sees ALL their missions (including inactive ones)
        so they can manage them from the dashboard.
        """
        missions = Mission.objects.filter(required_merchant=request.user.merchant_profile)
        return Response(MissionSerializer(missions, many=True, context={"request": request}).data)


class CustomerMissionViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerMissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = get_or_create_customer(self.request.user)
        return CustomerMission.objects.filter(customer=profile)

    @action(detail=False, methods=["get"])
    def my_missions(self, request):
        """
        Returns all ACTIVE missions with the customer's current progress.
        Pass ?merchant=<id> to scope to one merchant's missions.

        FIX: Previously only returned missions with an existing CustomerMission row.
        Now returns ALL active missions, creating a "0 progress" entry for new ones.
        """
        profile = get_or_create_customer(request.user)

        missions = Mission.objects.filter(is_active=True).select_related("required_merchant")
        merchant_id = request.query_params.get("merchant")
        if merchant_id:
            missions = missions.filter(required_merchant_id=merchant_id)

        # Build a progress map from existing CustomerMission rows
        progress_map = {
            cm.mission_id: cm
            for cm in CustomerMission.objects.filter(customer=profile, mission__in=missions)
        }

        data = []
        for mission in missions:
            cm = progress_map.get(mission.id)
            merchant = mission.required_merchant
            data.append({
                # Use the CustomerMission pk if it exists, otherwise use a "new-{id}" placeholder
                "id": cm.id if cm else f"new-{mission.id}",
                "mission": MissionSerializer(mission, context={"request": request}).data,
                "progress": cm.progress if cm else 0,
                "is_completed": cm.is_completed if cm else False,
                "completed_at": cm.completed_at if cm else None,
                # Surface merchant name so the frontend can display it
                "merchant_name": merchant.store_name if merchant else "",
            })

        return Response(data)


# ── Rewards ───────────────────────────────────────────────────────────────────

class RewardViewSet(viewsets.ModelViewSet):
    serializer_class = RewardSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "merchant_rewards", "toggle_active"]:
            return [IsAuthenticated(), IsMerchant()]
        # Customers and unauthenticated users can list/retrieve active rewards
        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user
        # Merchant editing their own rewards — return all (incl. inactive)
        if (
            self.action in ["update", "partial_update", "destroy"]
            and user.is_authenticated
            and hasattr(user, "merchant_profile")
        ):
            return Reward.objects.filter(merchant=user.merchant_profile)

        # Public listing: active only, optionally filtered by merchant
        queryset = Reward.objects.filter(is_active=True)
        merchant_id = self.request.query_params.get("merchant")
        if merchant_id:
            queryset = queryset.filter(merchant_id=merchant_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(merchant=self.request.user.merchant_profile)

    def perform_update(self, serializer):
        serializer.save(merchant=self.request.user.merchant_profile)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsMerchant])
    def merchant_rewards(self, request):
        """Get ALL rewards for the authenticated merchant (including inactive)."""
        rewards = Reward.objects.filter(merchant=request.user.merchant_profile)
        return Response(RewardSerializer(rewards, many=True, context={"request": request}).data)

    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated, IsMerchant])
    def toggle_active(self, request, pk=None):
        """Toggle is_active on a reward."""
        reward = self.get_object()
        if reward.merchant != request.user.merchant_profile:
            return Response({"error": "Not your reward."}, status=status.HTTP_403_FORBIDDEN)
        reward.is_active = not reward.is_active
        reward.save()
        return Response(RewardSerializer(reward).data)


# ── Redemptions ───────────────────────────────────────────────────────────────

class RedemptionViewSet(viewsets.ModelViewSet):
    serializer_class = RedemptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = get_or_create_customer(self.request.user)
        return Redemption.objects.filter(customer=profile)

    @action(detail=False, methods=["post"])
    def redeem(self, request):
        """
        Customer redeems a reward.
        Deducts points from Django CustomerProfile AND syncs back to Supabase.
        """
        reward_id = request.data.get("reward_id")
        if not reward_id:
            return Response({"error": "reward_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        profile = get_or_create_customer(request.user)

        try:
            reward = Reward.objects.get(id=reward_id, is_active=True)
        except Reward.DoesNotExist:
            return Response({"error": "Reward not found"}, status=status.HTTP_404_NOT_FOUND)

        if profile.loyalty_points < reward.points_cost:
            return Response(
                {"error": f"Not enough points. You have {profile.loyalty_points} pts, need {reward.points_cost} pts."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if reward.stock == 0:
            return Response({"error": "This reward is out of stock."}, status=status.HTTP_400_BAD_REQUEST)

        import uuid
        code = str(uuid.uuid4())[:8].upper()

        redemption = Redemption.objects.create(
            customer=profile,
            reward=reward,
            points_spent=reward.points_cost,
            code=code,
        )

        # Deduct points from Django CustomerProfile
        profile.loyalty_points -= reward.points_cost
        profile.save()

        # ── SYNC TO SUPABASE ──────────────────────────────────────────────
        # The frontend reads points from Supabase, so we must push the new
        # balance there as well. supabase_id is the UUID from Supabase Auth.
        supabase_id = str(request.user.supabase_id or "")
        if supabase_id:
            sync_points_to_supabase(supabase_id, profile.loyalty_points)
        # ─────────────────────────────────────────────────────────────────

        # Decrease stock if limited
        if reward.stock > 0:
            reward.stock -= 1
            reward.save()

        return Response(RedemptionSerializer(redemption).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def confirm_code(self, request):
        """Merchant confirms a redemption code — marks it redeemed."""
        if not hasattr(request.user, "merchant_profile"):
            return Response({"error": "Merchant access required."}, status=status.HTTP_403_FORBIDDEN)

        code = request.data.get("code", "").strip().upper()
        if not code:
            return Response({"error": "code is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            redemption = Redemption.objects.select_related("customer", "reward").get(
                code=code,
                status="pending",
                reward__merchant=request.user.merchant_profile,
            )
        except Redemption.DoesNotExist:
            return Response({"error": "Invalid or already used code."}, status=status.HTTP_404_NOT_FOUND)

        from django.utils import timezone
        redemption.status = "redeemed"
        redemption.redeemed_at = timezone.now()
        redemption.save()

        return Response({
            "success": True,
            "customer_name": redemption.customer.full_name or "Customer",
            "reward_name": redemption.reward.name,
            "points_spent": redemption.points_spent,
            "code": redemption.code,
        })

    @action(detail=False, methods=["post"])
    def manual_deduct(self, request):
        """
        Merchant manually deducts points from a customer by email.
        Deducts from Django AND syncs to Supabase so the customer sees it.
        """
        if not hasattr(request.user, "merchant_profile"):
            return Response({"error": "Merchant access required."}, status=status.HTTP_403_FORBIDDEN)

        from accounts.models import User
        email = request.data.get("email", "").strip()
        points = int(request.data.get("points", 0))

        if not email:
            return Response({"error": "Customer email is required."}, status=status.HTTP_400_BAD_REQUEST)
        if points <= 0:
            return Response({"error": "Points must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer_user = User.objects.get(email=email)
            profile = customer_user.customer_profile
        except (User.DoesNotExist, CustomerProfile.DoesNotExist):
            return Response({"error": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

        if profile.loyalty_points < points:
            return Response(
                {"error": f"Customer only has {profile.loyalty_points} pts."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile.loyalty_points -= points
        profile.save()

        # ── SYNC TO SUPABASE ──────────────────────────────────────────────
        supabase_id = str(customer_user.supabase_id or "")
        if supabase_id:
            sync_points_to_supabase(supabase_id, profile.loyalty_points)
        # ─────────────────────────────────────────────────────────────────

        return Response({
            "success": True,
            "customer_name": profile.full_name or email,
            "points_deducted": points,
            "new_balance": profile.loyalty_points,
        })


# ── Punch Cards ───────────────────────────────────────────────────────────────

class PunchCardViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PunchCardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = get_or_create_customer(self.request.user)
        return PunchCard.objects.filter(customer=profile)

    @action(detail=False, methods=["get"])
    def mine(self, request):
        merchant_id = request.query_params.get("merchant")
        if not merchant_id:
            return Response({"error": "merchant query param is required"}, status=status.HTTP_400_BAD_REQUEST)

        profile = get_or_create_customer(request.user)
        punch_card, _ = PunchCard.objects.get_or_create(
            customer=profile,
            merchant_id=merchant_id,
            defaults={"punches_to_free": 5},
        )
        return Response({
            "punch_count": punch_card.punch_count,
            "punches_to_free": punch_card.punches_to_free,
            "lifetime_punches": punch_card.lifetime_punches,
            "free_reward_available": punch_card.free_reward_available,
            "merchant_id": merchant_id,
        })

    @action(detail=False, methods=["post"])
    def use_free_reward(self, request):
        merchant_id = request.data.get("merchant_id")
        if not merchant_id:
            return Response({"error": "merchant_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        profile = get_or_create_customer(request.user)
        try:
            punch_card = PunchCard.objects.get(customer=profile, merchant_id=merchant_id)
        except PunchCard.DoesNotExist:
            return Response({"error": "Punch card not found"}, status=status.HTTP_404_NOT_FOUND)

        if not punch_card.free_reward_available:
            return Response({"error": "No free reward available"}, status=status.HTTP_400_BAD_REQUEST)

        punch_card.use_free_reward()
        return Response({
            "success": True,
            "punch_count": punch_card.punch_count,
            "punches_to_free": punch_card.punches_to_free,
        })


class MerchantPunchCardViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PunchCardSerializer
    permission_classes = [IsAuthenticated, IsMerchant]

    def get_queryset(self):
        return PunchCard.objects.filter(
            merchant=self.request.user.merchant_profile
        ).select_related("customer")