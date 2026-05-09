from rest_framework import serializers

from moderation.models import ModerationLog
from partner_programs.models import PartnerProgramVerificationRequest
from partner_programs.serializers.verification import (
    PartnerProgramVerificationRequestSerializer,
)
from partner_programs.verification_services import get_verification_rejection_reasons


class ModerationLogSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    actor = serializers.SerializerMethodField(method_name="get_author")
    program = serializers.SerializerMethodField()
    action_label = serializers.CharField(source="get_action_display", read_only=True)
    old_status = serializers.CharField(source="status_before", read_only=True)
    new_status = serializers.CharField(source="status_after", read_only=True)
    reason_code = serializers.CharField(source="rejection_reason", read_only=True)
    created_at = serializers.DateTimeField(source="datetime_created", read_only=True)

    class Meta:
        model = ModerationLog
        fields = [
            "id",
            "program",
            "author",
            "actor",
            "action",
            "action_label",
            "status_before",
            "status_after",
            "old_status",
            "new_status",
            "comment",
            "rejection_reason",
            "reason_code",
            "datetime_created",
            "created_at",
        ]

    def get_author(self, log: ModerationLog) -> dict | None:
        if not log.author:
            return None
        return {
            "id": log.author_id,
            "email": log.author.email,
            "full_name": log.author.get_full_name() or log.author.email,
        }

    def get_program(self, log: ModerationLog) -> dict:
        return {
            "id": log.program_id,
            "name": log.program.name,
            "tag": log.program.tag,
        }


class RejectionReasonSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()


class ModerationVerificationRequestSerializer(
    PartnerProgramVerificationRequestSerializer
):
    requests_history = serializers.SerializerMethodField()

    class Meta(PartnerProgramVerificationRequestSerializer.Meta):
        model = PartnerProgramVerificationRequest
        fields = PartnerProgramVerificationRequestSerializer.Meta.fields + [
            "requests_history",
        ]

    def get_requests_history(self, request_obj):
        history = (
            request_obj.program.verification_requests.select_related(
                "program",
                "company",
                "initiator",
                "decided_by",
            )
            .prefetch_related("documents")
            .order_by("-submitted_at", "-id")
        )
        return PartnerProgramVerificationRequestSerializer(history, many=True).data


class ModerationVerificationDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approve", "reject"))
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    reason_code = serializers.ChoiceField(
        choices=[reason["code"] for reason in get_verification_rejection_reasons()],
        required=False,
        allow_blank=True,
        default="",
    )
    rejection_reason = serializers.ChoiceField(
        choices=[reason["code"] for reason in get_verification_rejection_reasons()],
        required=False,
        allow_blank=True,
        default="",
    )

    def validate(self, attrs):
        attrs["reason_code"] = attrs.get("reason_code") or attrs.get(
            "rejection_reason",
            "",
        )
        attrs["rejection_reason"] = attrs["reason_code"]
        if attrs["decision"] == "reject":
            if not attrs.get("comment", "").strip():
                raise serializers.ValidationError(
                    {"comment": "Comment is required for rejection."}
                )
            if get_verification_rejection_reasons() and not attrs.get("reason_code"):
                raise serializers.ValidationError(
                    {"reason_code": "Rejection reason is required."}
                )
        return attrs


class ModerationVerificationRevokeSerializer(serializers.Serializer):
    comment = serializers.CharField()

    def validate_comment(self, value):
        if not value.strip():
            raise serializers.ValidationError("Comment is required for revocation.")
        return value
