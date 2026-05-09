from django.contrib import admin

from notifications.models import Notification, NotificationDelivery


class NotificationDeliveryInline(admin.TabularInline):
    model = NotificationDelivery
    extra = 0
    readonly_fields = ("channel", "status", "sent_at", "error")
    can_delete = False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "type", "title", "is_read", "created_at")
    list_filter = ("type", "is_read", "created_at")
    search_fields = ("recipient__email", "title", "message", "dedupe_key")
    readonly_fields = ("created_at", "dedupe_key")
    inlines = [NotificationDeliveryInline]


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ("id", "notification", "channel", "status", "sent_at")
    list_filter = ("channel", "status")
    search_fields = ("notification__recipient__email", "notification__title", "error")
