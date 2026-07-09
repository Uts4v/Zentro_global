from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "title", "message", "notification_type",
            "merchant_name", "context_url",
            "order_id", "merchant_id", "reward_id",
            "is_read", "created_at",
        ]
        read_only_fields = fields