from datetime import timedelta
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Notification
from .serializers import NotificationSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_list(request):
    """GET /api/notifications/ — last 7 days only"""
    one_week_ago = timezone.now() - timedelta(days=7)
    notifs = Notification.objects.filter(
        user=request.user,
        created_at__gte=one_week_ago,
    ).order_by("is_read", "-created_at")[:100]
    return Response(NotificationSerializer(notifs, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unread_count(request):
    """GET /api/notifications/unread-count/"""
    one_week_ago = timezone.now() - timedelta(days=7)
    count = Notification.objects.filter(
        user=request.user,
        is_read=False,
        created_at__gte=one_week_ago,
    ).count()
    return Response({"unread_count": count})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def mark_read(request, pk):
    """PATCH /api/notifications/<pk>/read/"""
    try:
        notif = Notification.objects.get(pk=pk, user=request.user)
    except Notification.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    notif.is_read = True
    notif.save(update_fields=["is_read"])
    return Response(NotificationSerializer(notif).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    """POST /api/notifications/read-all/"""
    Notification.objects.filter(
        user=request.user, is_read=False
    ).update(is_read=True)
    return Response({"status": "ok"})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def clear_all(request):
    """DELETE /api/notifications/clear/ — delete all notifications for user"""
    Notification.objects.filter(user=request.user).delete()
    return Response({"status": "cleared"})