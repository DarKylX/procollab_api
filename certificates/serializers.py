from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from certificates.enums import (
    CERTIFICATE_TYPE_PARTICIPATION,
    ISSUE_CONDITION_SUBMITTED_PROJECT,
    RELEASE_MODE_CHOICES,
    get_font_options,
)
from certificates.models import (
    CertificateGenerationRun,
    IssuedCertificate,
    ProgramCertificateTemplate,
)
from certificates.services import (
    get_participant_full_name,
    DEFAULT_COMPANY_LOGO_POSITION,
    DEFAULT_SIGNATURE_POSITION,
    DEFAULT_STAMP_POSITION,
    normalize_fields_positioning,
    validate_asset_position,
    upload_background_image,
    upload_certificate_asset_image,
    validate_background_file_metadata,
    validate_certificate_asset_file_metadata,
    validate_fields_positioning,
    validate_uploaded_background_file,
    validate_uploaded_certificate_asset_file,
)
from files.models import UserFile
from files.serializers import UserFileSerializer


class UserFileReferenceField(serializers.PrimaryKeyRelatedField):
    def use_pk_only_optimization(self):
        return False

    def to_internal_value(self, data):
        if isinstance(data, str) and not data.isdigit():
            try:
                return self.get_queryset().get(link=data)
            except UserFile.DoesNotExist:
                self.fail("does_not_exist", pk_value=data)
        return super().to_internal_value(data)

    def to_representation(self, value):
        return getattr(value, "link", None)


class ProgramCertificateTemplateSerializer(serializers.ModelSerializer):
    background_file = UserFileReferenceField(
        source="background_image",
        queryset=UserFile.objects.all(),
        required=False,
        allow_null=True,
    )
    background_file_meta = serializers.SerializerMethodField()
    background_image = serializers.PrimaryKeyRelatedField(
        queryset=UserFile.objects.all(),
        required=False,
        allow_null=True,
    )
    background_image_id = serializers.PrimaryKeyRelatedField(
        queryset=UserFile.objects.all(),
        source="background_image",
        required=False,
        allow_null=True,
        write_only=True,
    )
    background_image_file = serializers.FileField(required=False, write_only=True)
    signature_file = UserFileReferenceField(
        source="signature_image",
        queryset=UserFile.objects.all(),
        required=False,
        allow_null=True,
    )
    signature_file_meta = serializers.SerializerMethodField()
    signature_image = serializers.PrimaryKeyRelatedField(
        queryset=UserFile.objects.all(),
        required=False,
        allow_null=True,
    )
    signature_image_id = serializers.PrimaryKeyRelatedField(
        queryset=UserFile.objects.all(),
        source="signature_image",
        required=False,
        allow_null=True,
        write_only=True,
    )
    signature_image_file = serializers.FileField(required=False, write_only=True)
    stamp_file = UserFileReferenceField(
        source="stamp_image",
        queryset=UserFile.objects.all(),
        required=False,
        allow_null=True,
    )
    stamp_file_meta = serializers.SerializerMethodField()
    stamp_image = serializers.PrimaryKeyRelatedField(
        queryset=UserFile.objects.all(),
        required=False,
        allow_null=True,
    )
    stamp_image_id = serializers.PrimaryKeyRelatedField(
        queryset=UserFile.objects.all(),
        source="stamp_image",
        required=False,
        allow_null=True,
        write_only=True,
    )
    stamp_image_file = serializers.FileField(required=False, write_only=True)
    company_logo_file = UserFileReferenceField(
        source="company_logo_image",
        queryset=UserFile.objects.all(),
        required=False,
        allow_null=True,
    )
    company_logo_file_meta = serializers.SerializerMethodField()
    company_logo_image = serializers.PrimaryKeyRelatedField(
        queryset=UserFile.objects.all(),
        required=False,
        allow_null=True,
    )
    company_logo_image_id = serializers.PrimaryKeyRelatedField(
        queryset=UserFile.objects.all(),
        source="company_logo_image",
        required=False,
        allow_null=True,
        write_only=True,
    )
    company_logo_image_file = serializers.FileField(required=False, write_only=True)
    issue_rule = serializers.CharField(source="issue_condition_type", required=False)
    field_positions = serializers.JSONField(source="fields_positioning", required=False)
    is_configured = serializers.SerializerMethodField()
    program = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ProgramCertificateTemplate
        fields = [
            "id",
            "program",
            "is_enabled",
            "issue_rule",
            "issue_condition_type",
            "release_mode",
            "certificate_type",
            "show_project_title",
            "show_team_members",
            "show_rank",
            "template_name",
            "background_file",
            "background_file_meta",
            "background_image",
            "background_image_id",
            "background_image_file",
            "signature_file",
            "signature_file_meta",
            "signature_image",
            "signature_image_id",
            "signature_image_file",
            "signature_position",
            "stamp_file",
            "stamp_file_meta",
            "stamp_image",
            "stamp_image_id",
            "stamp_image_file",
            "stamp_position",
            "company_logo_file",
            "company_logo_file_meta",
            "company_logo_image",
            "company_logo_image_id",
            "company_logo_image_file",
            "company_logo_position",
            "signer_name",
            "text_color",
            "accent_text_color",
            "font_family",
            "field_positions",
            "fields_positioning",
            "min_score",
            "top_positions",
            "generated_at",
            "released_at",
            "is_configured",
            "datetime_created",
            "datetime_updated",
        ]
        read_only_fields = [
            "id",
            "program",
            "background_file_meta",
            "signature_file_meta",
            "stamp_file_meta",
            "company_logo_file_meta",
            "generated_at",
            "datetime_created",
            "datetime_updated",
        ]

    def get_background_file_meta(self, obj):
        if not getattr(obj, "background_image", None):
            return None
        return UserFileSerializer(obj.background_image).data

    def get_signature_file_meta(self, obj):
        if not getattr(obj, "signature_image", None):
            return None
        return UserFileSerializer(obj.signature_image).data

    def get_stamp_file_meta(self, obj):
        if not getattr(obj, "stamp_image", None):
            return None
        return UserFileSerializer(obj.stamp_image).data

    def get_company_logo_file_meta(self, obj):
        if not getattr(obj, "company_logo_image", None):
            return None
        return UserFileSerializer(obj.company_logo_image).data

    def get_is_configured(self, obj):
        return bool(getattr(obj, "pk", None))

    def validate_background_file(self, value):
        if value is not None:
            validate_background_file_metadata(value)
        return value

    def validate_background_image(self, value):
        if value is not None:
            validate_background_file_metadata(value)
        return value

    def validate_background_image_id(self, value):
        if value is not None:
            validate_background_file_metadata(value)
        return value

    def validate_background_image_file(self, value):
        validate_uploaded_background_file(value)
        return value

    def validate_signature_file(self, value):
        if value is not None:
            validate_certificate_asset_file_metadata(value)
        return value

    def validate_signature_image(self, value):
        if value is not None:
            validate_certificate_asset_file_metadata(value)
        return value

    def validate_signature_image_id(self, value):
        if value is not None:
            validate_certificate_asset_file_metadata(value)
        return value

    def validate_signature_image_file(self, value):
        validate_uploaded_certificate_asset_file(value)
        return value

    def validate_stamp_file(self, value):
        if value is not None:
            validate_certificate_asset_file_metadata(value)
        return value

    def validate_stamp_image(self, value):
        if value is not None:
            validate_certificate_asset_file_metadata(value)
        return value

    def validate_stamp_image_id(self, value):
        if value is not None:
            validate_certificate_asset_file_metadata(value)
        return value

    def validate_stamp_image_file(self, value):
        validate_uploaded_certificate_asset_file(value)
        return value

    def validate_company_logo_file(self, value):
        if value is not None:
            validate_certificate_asset_file_metadata(value)
        return value

    def validate_company_logo_image(self, value):
        if value is not None:
            validate_certificate_asset_file_metadata(value)
        return value

    def validate_company_logo_image_id(self, value):
        if value is not None:
            validate_certificate_asset_file_metadata(value)
        return value

    def validate_company_logo_image_file(self, value):
        validate_uploaded_certificate_asset_file(value)
        return value

    def validate_signature_position(self, value):
        return validate_asset_position(value, DEFAULT_SIGNATURE_POSITION)

    def validate_stamp_position(self, value):
        return validate_asset_position(value, DEFAULT_STAMP_POSITION)

    def validate_company_logo_position(self, value):
        return validate_asset_position(value, DEFAULT_COMPANY_LOGO_POSITION)

    def validate_field_positions(self, value):
        return validate_fields_positioning(value)

    def validate_fields_positioning(self, value):
        return validate_fields_positioning(value)

    def validate_issue_rule(self, value):
        return self._validate_issue_rule(value)

    def validate_issue_condition_type(self, value):
        return self._validate_issue_rule(value)

    def validate_certificate_type(self, value):
        if value != CERTIFICATE_TYPE_PARTICIPATION:
            raise serializers.ValidationError("Only participation certificates are supported.")
        return value

    def validate_release_mode(self, value):
        allowed_values = {choice[0] for choice in RELEASE_MODE_CHOICES}
        if value not in allowed_values:
            raise serializers.ValidationError("Unsupported release mode.")
        return value

    def validate(self, attrs):
        attrs["issue_condition_type"] = ISSUE_CONDITION_SUBMITTED_PROJECT
        attrs["certificate_type"] = CERTIFICATE_TYPE_PARTICIPATION
        if "fields_positioning" in attrs:
            attrs["fields_positioning"] = normalize_fields_positioning(
                attrs["fields_positioning"]
            )
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        field_positions = data.get("field_positions") or data.get("fields_positioning")
        normalized_positions = normalize_fields_positioning(field_positions)
        data["issue_rule"] = ISSUE_CONDITION_SUBMITTED_PROJECT
        data["issue_condition_type"] = ISSUE_CONDITION_SUBMITTED_PROJECT
        data["certificate_type"] = CERTIFICATE_TYPE_PARTICIPATION
        data["field_positions"] = normalized_positions
        data["fields_positioning"] = normalized_positions
        return data

    def _validate_issue_rule(self, value):
        if value != ISSUE_CONDITION_SUBMITTED_PROJECT:
            raise serializers.ValidationError("Only submitted_project is supported.")
        return value

    def _upload_background_image_file(self, attrs):
        uploaded_file = attrs.pop("background_image_file", None)
        if uploaded_file is None:
            return attrs

        request = self.context.get("request")
        user = getattr(request, "user", None)
        attrs["background_image"] = upload_background_image(uploaded_file, user)
        return attrs

    def _upload_asset_image_files(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        for upload_key, model_key in (
            ("signature_image_file", "signature_image"),
            ("stamp_image_file", "stamp_image"),
            ("company_logo_image_file", "company_logo_image"),
        ):
            uploaded_file = attrs.pop(upload_key, None)
            if uploaded_file is not None:
                attrs[model_key] = upload_certificate_asset_image(uploaded_file, user)
        return attrs

    def create(self, validated_data):
        validated_data = self._upload_background_image_file(validated_data)
        validated_data = self._upload_asset_image_files(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._upload_background_image_file(validated_data)
        validated_data = self._upload_asset_image_files(validated_data)
        return super().update(instance, validated_data)


class CertificateFontSerializer(serializers.Serializer):
    id = serializers.CharField()
    label = serializers.CharField()


def get_serialized_font_options():
    return CertificateFontSerializer(get_font_options(), many=True).data


class IssuedCertificateSerializer(serializers.ModelSerializer):
    participant = serializers.IntegerField(source="user_id", read_only=True)
    participant_full_name = serializers.SerializerMethodField()
    program_project = serializers.IntegerField(source="program_project_id", read_only=True)
    project_title = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = IssuedCertificate
        fields = [
            "id",
            "program",
            "participant",
            "user",
            "program_project",
            "project_title",
            "participant_full_name",
            "team_name",
            "final_score",
            "rating_position",
            "certificate_uuid",
            "certificate_id",
            "status",
            "pdf_url",
            "download_url",
            "generated_at",
            "issued_at",
            "downloaded_at",
        ]
        read_only_fields = fields

    def get_participant_full_name(self, obj):
        return get_participant_full_name(obj.user)

    def get_project_title(self, obj):
        project = getattr(getattr(obj, "program_project", None), "project", None)
        return getattr(project, "name", None) or ""

    def get_pdf_url(self, obj):
        return obj.pdf_file.link if obj.pdf_file_id else ""

    def get_download_url(self, obj):
        return f"/programs/{obj.program_id}/certificate/{obj.certificate_id}/download/"


class PublicCertificateVerificationSerializer(serializers.ModelSerializer):
    is_valid = serializers.SerializerMethodField()
    participant_full_name = serializers.SerializerMethodField()
    program_name = serializers.CharField(source="program.name")
    program_finished_at = serializers.DateTimeField(source="program.datetime_finished")
    certificate_issued_at = serializers.DateTimeField(source="issued_at")
    organizer_name = serializers.SerializerMethodField()
    is_organizer_verified = serializers.SerializerMethodField()
    final_score = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = IssuedCertificate
        fields = [
            "is_valid",
            "certificate_uuid",
            "participant_full_name",
            "program_name",
            "program_finished_at",
            "certificate_issued_at",
            "organizer_name",
            "is_organizer_verified",
            "team_name",
            "rating_position",
            "final_score",
        ]

    def get_is_valid(self, obj):
        return obj.status == IssuedCertificate.STATUS_GENERATED

    def get_participant_full_name(self, obj):
        return get_participant_full_name(obj.user)

    def get_organizer_name(self, obj):
        company = getattr(obj.program, "company", None)
        return getattr(company, "name", None) or None

    def get_is_organizer_verified(self, obj):
        return obj.program.verification_status == "verified"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for optional_field in (
            "organizer_name",
            "team_name",
            "rating_position",
            "final_score",
        ):
            if data.get(optional_field) in (None, ""):
                data.pop(optional_field, None)
        return data


class CertificateGenerationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificateGenerationRun
        fields = [
            "id",
            "program",
            "status",
            "total_expected",
            "enqueued_count",
            "issued_count",
            "error_count",
            "error_message",
            "started_at",
            "completed_at",
            "datetime_updated",
        ]
        read_only_fields = fields


class CertificateGenerationStatsSerializer(serializers.Serializer):
    issued_count = serializers.IntegerField()
    generated_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    eligible_count = serializers.IntegerField()
    error_count = serializers.IntegerField()
    last_run = CertificateGenerationRunSerializer(allow_null=True)


def raise_drf_validation(exc: DjangoValidationError):
    raise serializers.ValidationError(exc.messages)
