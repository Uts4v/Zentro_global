from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "user", "target_model", "target_id", "ip_address", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("user__email", "target_model", "target_id", "ip_address")
    readonly_fields = [f.name for f in AuditLog._meta.get_fields() if hasattr(f, "name")]
    ordering = ("-created_at",)
