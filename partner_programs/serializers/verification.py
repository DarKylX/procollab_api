from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from files.models import UserFile
from files.serializers import UserFileSerializer
from partner_programs.models import PartnerProgram, PartnerProgramVerificationRequest
from partner_programs.verification_services import (
    effective_verification_status,
    latest_approved_verification_request,
    latest_verification_request,
    verification_requests_for_program,
)
from projects.models import Company
from projects.validators import inn_validator


MAX_DOCUMENTS = 5
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/jpg", "image/png"}


class CompanyBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ("id", "name", "inn")


class VerificationCompanyInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    inn = serializers.CharField(max_length=12)

    def validate_inn(self, value):
        normalized = value.strip()
        try:
            inn_validator(normalized)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return normalized


class PartnerProgramVerificationRequestSerializer(serializers.ModelSerializer):
    program = serializers.SerializerMethodField()
    company = CompanyBriefSerializer(read_only=True)
    initiator = serializers.SerializerMethodField()
    submitted_by = serializers.SerializerMethodField(method_name="get_initiator")
    decided_by = serializers.SerializerMethodField()
    reviewed_by = serializers.SerializerMethodField(method_name="get_decided_by")
    reviewed_at = serializers.DateTimeField(source="decided_at", read_only=True)
    reason_code = serializers.CharField(source="rejection_reason", read_only=True)
    documents = UserFileSerializer(many=True, read_only=True)
    rejection_reason_label = serializers.CharField(
        source="get_rejection_reason_display",
        read_only=True,
    )

    class Meta:
        model = PartnerProgramVerificationRequest
        fields = [
            "id",
            "program",
            "company",
            "company_name",
            "inn",
            "legal_name",
            "ogrn",
            "website",
            "region",
            "initiator",
            "submitted_by",
            "contact_full_name",
            "contact_position",
            "contact_email",
            "contact_phone",
            "company_role_description",
            "documents",
            "status",
            "submitted_at",
            "decided_at",
            "reviewed_at",
            "decided_by",
            "reviewed_by",
            "admin_comment",
            "rejection_reason",
            "reason_code",
            "rejection_reason_label",
        ]

    def get_program(self, request_obj):
        return {
            "id": request_obj.program_id,
            "name": request_obj.program.name,
            "tag": request_obj.program.tag,
            "status": request_obj.program.status,
            "verification_status": request_obj.program.verification_status,
        }

    def get_initiator(self, request_obj):
        return _user_summary(request_obj.initiator)

    def get_decided_by(self, request_obj):
        return _user_summary(request_obj.decided_by)


class PartnerProgramVerificationSubmitSerializer(serializers.Serializer):
    company_id = serializers.IntegerField(required=False)
    company = VerificationCompanyInputSerializer(required=False)
    company_name = serializers.CharField(max_length=255, required=False)
    inn = serializers.CharField(max_length=12, required=False)
    legal_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )
    ogrn = serializers.CharField(
        max_length=32,
        required=False,
        allow_blank=True,
        default="",
    )
    website = serializers.URLField(required=False, allow_blank=True, default="")
    region = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )
    contact_full_name = serializers.CharField(max_length=255)
    contact_position = serializers.CharField(max_length=255)
    contact_email = serializers.EmailField()
    contact_phone = serializers.CharField(max_length=64)
    company_role_description = serializers.CharField()
    documents = serializers.SlugRelatedField(
        slug_field="link",
        queryset=UserFile.objects.all(),
        many=True,
        required=False,
        default=list,
    )

    def validate(self, attrs):
        company_id = attrs.pop("company_id", None)
        company_data = attrs.pop("company", None)
        if company_id and company_data:
            raise serializers.ValidationError(
                {"company": "Pass either company_id or company, not both."}
            )

        company_name = (attrs.get("company_name") or "").strip()
        inn = (attrs.get("inn") or "").strip()
        if company_data:
            company_name = company_data["name"].strip()
            inn = company_data["inn"].strip()

        if company_id:
            try:
                company = Company.objects.get(pk=company_id)
            except Company.DoesNotExist:
                raise serializers.ValidationError({"company_id": "Company not found."})
            company_name = company_name or company.name
            inn = inn or company.inn
            attrs["company"] = company

        if not company_id and not company_data and (not company_name or not inn):
            raise serializers.ValidationError(
                {"company": "Pass company_name and inn, or existing company_id."}
            )

        try:
            inn_validator(inn)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"inn": exc.messages})

        if "company" not in attrs:
            company = Company.objects.filter(inn=inn).first()
            if company is None:
                company = Company(name=company_name, inn=inn)
                try:
                    company.full_clean()
                except DjangoValidationError as exc:
                    raise serializers.ValidationError(exc.message_dict)
                company.save()
            attrs["company"] = company

        attrs["company_name"] = company_name
        attrs["inn"] = inn
        attrs["legal_name"] = (attrs.get("legal_name") or "").strip()
        attrs["ogrn"] = (attrs.get("ogrn") or "").strip()
        attrs["website"] = (attrs.get("website") or "").strip()
        attrs["region"] = (attrs.get("region") or "").strip()

        documents = attrs.get("documents", [])
        _validate_documents(documents)
        return attrs


class PartnerProgramVerificationStatusSerializer(serializers.Serializer):
    verification_status = serializers.CharField()
    current_status = serializers.CharField()
    is_verified = serializers.BooleanField()
    verified_company_name = serializers.CharField(allow_blank=True)
    company_data = serializers.DictField(allow_null=True)
    latest_submitted_at = serializers.DateTimeField(allow_null=True)
    decided_at = serializers.DateTimeField(allow_null=True)
    rejection_reason = serializers.CharField(allow_blank=True)
    admin_comment = serializers.CharField(allow_blank=True)
    latest_request = PartnerProgramVerificationRequestSerializer(allow_null=True)
    requests_history = PartnerProgramVerificationRequestSerializer(many=True)
    history = PartnerProgramVerificationRequestSerializer(many=True)

    @classmethod
    def build_payload(cls, program: PartnerProgram, user=None) -> dict:
        effective_status = effective_verification_status(program, user=user)
        latest_request = latest_verification_request(program, user=user)
        latest_approved_request = latest_approved_verification_request(program, user=user)
        history = (
            verification_requests_for_program(program, user=user)
            .select_related(
                "program",
                "company",
                "initiator",
                "decided_by",
            )
            .prefetch_related("documents")
            .order_by("-submitted_at", "-id")
        )
        verified_company_name = ""
        if latest_approved_request:
            verified_company_name = latest_approved_request.company_name or ""
        return {
            "verification_status": effective_status,
            "current_status": effective_status,
            "is_verified": program.verification_status
            == PartnerProgram.VERIFICATION_STATUS_VERIFIED,
            "verified_company_name": verified_company_name,
            "company_data": _request_company_data(latest_request),
            "latest_submitted_at": latest_request.submitted_at
            if latest_request
            else None,
            "decided_at": latest_request.decided_at if latest_request else None,
            "rejection_reason": (
                latest_request.rejection_reason
                if latest_request
                and latest_request.status == PartnerProgramVerificationRequest.STATUS_REJECTED
                else ""
            ),
            "admin_comment": (
                latest_request.admin_comment
                if latest_request
                and latest_request.status == PartnerProgramVerificationRequest.STATUS_REJECTED
                else ""
            ),
            "latest_request": latest_request,
            "requests_history": history,
            "history": history,
        }


def _validate_documents(documents):
    if not documents:
        raise serializers.ValidationError(
            {"documents": "Attach at least one verification document."}
        )

    if len(documents) > MAX_DOCUMENTS:
        raise serializers.ValidationError(
            {"documents": f"Attach no more than {MAX_DOCUMENTS} documents."}
        )

    for document in documents:
        if document.size > MAX_DOCUMENT_SIZE:
            raise serializers.ValidationError(
                {"documents": "Each document must be no larger than 10 MB."}
            )
        extension = (document.extension or "").lower().lstrip(".")
        mime_type = (document.mime_type or "").lower()
        if extension not in ALLOWED_EXTENSIONS and mime_type not in ALLOWED_MIME_TYPES:
            raise serializers.ValidationError(
                {"documents": "Allowed document formats are PDF, JPG and PNG."}
            )


def _user_summary(user):
    if not user:
        return None
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.get_full_name(),
    }


def _request_company_data(request_obj):
    if not request_obj:
        return None
    return {
        "company_name": request_obj.company_name,
        "inn": request_obj.inn,
        "legal_name": request_obj.legal_name,
        "ogrn": request_obj.ogrn,
        "website": request_obj.website,
        "region": request_obj.region,
    }
