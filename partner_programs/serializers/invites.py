from rest_framework import serializers

from partner_programs.models import PartnerProgramInvite
from partner_programs.services import build_program_invite_url, get_program_organizer_name


class PartnerProgramInviteCreateSerializer(serializers.Serializer):
    emails = serializers.ListField(
        child=serializers.EmailField(),
        allow_empty=False,
        required=False,
    )
    email = serializers.EmailField(required=False)
    expires_in_days = serializers.IntegerField(
        min_value=1,
        max_value=365,
        required=False,
        default=30,
    )
    custom_message = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
    )

    def validate(self, attrs):
        emails = attrs.get("emails") or []
        single_email = attrs.get("email")
        if single_email:
            emails.append(single_email)
        if not emails:
            raise serializers.ValidationError(
                {"emails": "Передайте email или список emails."}
            )
        attrs["emails"] = list(dict.fromkeys(email.lower() for email in emails))
        return attrs


class PartnerProgramInviteSerializer(serializers.ModelSerializer):
    token = serializers.UUIDField(read_only=True)
    accept_url = serializers.SerializerMethodField()
    accepted_by_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PartnerProgramInvite
        fields = [
            "id",
            "program",
            "email",
            "token",
            "accept_url",
            "status",
            "datetime_created",
            "accepted_at",
            "expires_at",
            "accepted_by",
            "accepted_by_name",
            "created_by",
            "created_by_name",
        ]
        read_only_fields = fields

    def get_accept_url(self, obj):
        return build_program_invite_url(obj.token)

    def get_accepted_by_name(self, obj):
        return self._user_name(obj.accepted_by)

    def get_created_by_name(self, obj):
        return self._user_name(obj.created_by)

    def _user_name(self, user):
        if not user:
            return None
        full_name = user.get_full_name()
        return full_name or user.email


class PublicPartnerProgramInviteSerializer(serializers.ModelSerializer):
    program_id = serializers.IntegerField(source="program.id", read_only=True)
    program_name = serializers.CharField(source="program.name", read_only=True)
    organizer_name = serializers.SerializerMethodField()
    accept_url = serializers.SerializerMethodField()

    class Meta:
        model = PartnerProgramInvite
        fields = [
            "token",
            "email",
            "status",
            "program_id",
            "program_name",
            "organizer_name",
            "expires_at",
            "accept_url",
        ]

    def get_organizer_name(self, obj):
        return get_program_organizer_name(obj.program)

    def get_accept_url(self, obj):
        return build_program_invite_url(obj.token)
