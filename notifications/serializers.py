from rest_framework import serializers

from notifications.models import Notification


NOTIFICATION_CATEGORIES = {
    Notification.Type.PROGRAM_SUBMITTED_TO_MODERATION: "moderation",
    Notification.Type.PROGRAM_MODERATION_APPROVED: "moderation",
    Notification.Type.PROGRAM_MODERATION_REJECTED: "moderation",
    Notification.Type.COMPANY_VERIFICATION_SUBMITTED: "verification",
    Notification.Type.COMPANY_VERIFICATION_APPROVED: "verification",
    Notification.Type.COMPANY_VERIFICATION_REJECTED: "verification",
    Notification.Type.EXPERT_PROJECTS_ASSIGNED: "expertise",
}


class NotificationSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "title",
            "message",
            "object_type",
            "object_id",
            "url",
            "is_read",
            "created_at",
            "category",
        ]

    def get_category(self, notification):
        return NOTIFICATION_CATEGORIES.get(notification.type, "other")
