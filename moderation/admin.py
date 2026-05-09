from django.contrib import admin

from moderation.models import ModerationLog


@admin.register(ModerationLog)
class ModerationLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "program",
        "author",
        "action",
        "status_before",
        "status_after",
        "datetime_created",
    )
    list_filter = ("action", "status_before", "status_after")
    search_fields = ("program__name", "program__tag", "author__email", "comment")
    readonly_fields = ("datetime_created",)
