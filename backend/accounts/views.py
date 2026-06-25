# accounts/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import CustomerProfile


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """Return the authenticated user's profile and loyalty points."""
    user = request.user
    try:
        profile = user.customer_profile
        return Response({
            "id": str(user.supabase_id or user.id),
            "email": user.email,
            "full_name": profile.full_name or user.email,
            "loyalty_points": profile.loyalty_points,
            "streak_days": profile.streak_days,
            "total_orders": profile.total_orders,
            "tier": profile.tier,
        })
    except CustomerProfile.DoesNotExist:
        return Response({
            "id": str(user.supabase_id or user.id),
            "email": user.email,
            "full_name": user.email,
            "loyalty_points": 0,
            "streak_days": 0,
            "total_orders": 0,
            "tier": "bronze",
        })