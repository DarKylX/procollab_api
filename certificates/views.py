from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views import View
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from certificates.models import IssuedCertificate, ProgramCertificateTemplate
from certificates.serializers import (
    CertificateGenerationRunSerializer,
    CertificateGenerationStatsSerializer,
    IssuedCertificateSerializer,
    ProgramCertificateTemplateSerializer,
    PublicCertificateVerificationSerializer,
    get_serialized_font_options,
)
from certificates.services import (
    CertificateTemplateConflictError,
    ensure_template_can_be_deleted,
    get_certificate_stats,
    get_participant_certificate_state,
    is_certificate_released_for_participant,
    read_user_file_bytes,
    render_certificate_preview_html,
    render_certificate_preview_pdf,
    generate_certificates_for_program_sync,
)
from partner_programs.models import PartnerProgram, PartnerProgramUserProfile


CERTIFICATE_NOT_FOUND_MESSAGE = "Сертификат с указанным идентификатором не найден."
INVALID_CERTIFICATE_UUID_MESSAGE = "Некорректный формат идентификатора сертификата."


def parse_certificate_uuid(value):
    try:
        return UUID(str(value))
    except (AttributeError, TypeError, ValueError):
        return None


def get_public_certificate(certificate_uuid):
    return (
        IssuedCertificate.objects.select_related("program__company", "user")
        .filter(certificate_uuid=certificate_uuid)
        .first()
    )


class CertificateTemplateAccessMixin:
    def get_program(self, pk):
        return get_object_or_404(PartnerProgram, pk=pk)

    def has_program_access(self, user, program):
        return bool(
            getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
            or program.is_manager(user)
        )

    def get_program_or_response(self, request, pk):
        program = self.get_program(pk)
        if not self.has_program_access(request.user, program):
            return program, Response(
                {"detail": "Insufficient permissions."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return program, None

    def get_serializer_data(self, request):
        data = request.data.copy()
        uploaded_background = request.FILES.get("background_file") or request.FILES.get(
            "background_image"
        )
        if uploaded_background is not None and "background_image_file" not in data:
            data["background_image_file"] = uploaded_background
            data.pop("background_file", None)
            data.pop("background_image", None)
        uploaded_signature = request.FILES.get("signature_file") or request.FILES.get(
            "signature_image"
        )
        if uploaded_signature is not None and "signature_image_file" not in data:
            data["signature_image_file"] = uploaded_signature
            data.pop("signature_file", None)
            data.pop("signature_image", None)
        uploaded_stamp = request.FILES.get("stamp_file") or request.FILES.get(
            "stamp_image"
        )
        if uploaded_stamp is not None and "stamp_image_file" not in data:
            data["stamp_image_file"] = uploaded_stamp
            data.pop("stamp_file", None)
            data.pop("stamp_image", None)
        uploaded_company_logo = request.FILES.get("company_logo_file") or request.FILES.get(
            "company_logo_image"
        )
        if uploaded_company_logo is not None and "company_logo_image_file" not in data:
            data["company_logo_image_file"] = uploaded_company_logo
            data.pop("company_logo_file", None)
            data.pop("company_logo_image", None)
        return data

    def serialize_template(self, template):
        return ProgramCertificateTemplateSerializer(template).data


class ProgramCertificateTemplateView(CertificateTemplateAccessMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]
    return_default_when_missing = True

    def get(self, request, pk):
        program, error_response = self.get_program_or_response(request, pk)
        if error_response is not None:
            return error_response

        try:
            template = program.certificate_template
        except ProgramCertificateTemplate.DoesNotExist:
            if not self.return_default_when_missing:
                return Response(
                    {"detail": "Certificate template was not created."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            template = ProgramCertificateTemplate(program=program)

        return Response(self.serialize_template(template))

    def put(self, request, pk):
        return self._upsert(request, pk)

    def patch(self, request, pk):
        return self._upsert(request, pk)

    def delete(self, request, pk):
        program, error_response = self.get_program_or_response(request, pk)
        if error_response is not None:
            return error_response

        try:
            template = program.certificate_template
        except ProgramCertificateTemplate.DoesNotExist:
            return Response(
                {"detail": "Certificate template was not created."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            ensure_template_can_be_deleted(template)
        except CertificateTemplateConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        template.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _upsert(self, request, pk):
        program, error_response = self.get_program_or_response(request, pk)
        if error_response is not None:
            return error_response

        try:
            template = program.certificate_template
        except ProgramCertificateTemplate.DoesNotExist:
            template = None
        serializer = ProgramCertificateTemplateSerializer(
            template,
            data=self.get_serializer_data(request),
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        saved_template = serializer.save(program=program)
        response_status = status.HTTP_200_OK if template else status.HTTP_201_CREATED
        return Response(
            ProgramCertificateTemplateSerializer(saved_template).data,
            status=response_status,
        )


class ProgramCertificateLegacyTemplateView(ProgramCertificateTemplateView):
    return_default_when_missing = False


class ProgramCertificateTemplatePreviewView(CertificateTemplateAccessMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            template_data = self.get_validated_template_data(request, pk)
        except PermissionError:
            return Response(
                {"detail": "Insufficient permissions."},
                status=status.HTTP_403_FORBIDDEN,
            )
        html = render_certificate_preview_html(template_data)
        return HttpResponse(html, content_type="text/html; charset=utf-8")

    def get_validated_template_data(self, request, pk):
        program, error_response = self.get_program_or_response(request, pk)
        if error_response is not None:
            raise PermissionError("Insufficient permissions.")

        try:
            template = program.certificate_template
        except ProgramCertificateTemplate.DoesNotExist:
            template = None
        serializer = ProgramCertificateTemplateSerializer(
            template,
            data=self.get_serializer_data(request),
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        template_data = {}
        if template is not None:
            template_data = {
                "background_image": template.background_image,
                "signature_image": template.signature_image,
                "stamp_image": template.stamp_image,
                "company_logo_image": template.company_logo_image,
                "signature_position": template.signature_position,
                "stamp_position": template.stamp_position,
                "company_logo_position": template.company_logo_position,
                "signer_name": template.signer_name,
                "font_family": template.font_family,
                "text_color": template.text_color,
                "accent_text_color": template.accent_text_color,
                "fields_positioning": template.fields_positioning,
            }
        template_data.update(serializer.validated_data)
        template_data.pop("background_image_file", None)
        template_data.pop("signature_image_file", None)
        template_data.pop("stamp_image_file", None)
        template_data.pop("company_logo_image_file", None)
        return template_data


class ProgramCertificatePreviewPdfView(ProgramCertificateTemplatePreviewView):
    def post(self, request, pk):
        try:
            template_data = self.get_validated_template_data(request, pk)
        except PermissionError:
            return Response(
                {"detail": "Insufficient permissions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        pdf_bytes = render_certificate_preview_pdf(template_data)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="certificate-preview.pdf"'
        return response


class CertificateFontListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(get_serialized_font_options())


class ProgramCertificateGenerationStatsView(CertificateTemplateAccessMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        program, error_response = self.get_program_or_response(request, pk)
        if error_response is not None:
            return error_response
        return Response(CertificateGenerationStatsSerializer(get_certificate_stats(program)).data)


class ProgramCertificateGenerationStartView(CertificateTemplateAccessMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        program, error_response = self.get_program_or_response(request, pk)
        if error_response is not None:
            return error_response

        regenerate = bool(request.data.get("regenerate", True))
        try:
            run = generate_certificates_for_program_sync(
                program,
                regenerate=regenerate,
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "run": CertificateGenerationRunSerializer(run).data,
                "stats": CertificateGenerationStatsSerializer(
                    get_certificate_stats(program)
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class ProgramCertificateReleaseView(CertificateTemplateAccessMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        program, error_response = self.get_program_or_response(request, pk)
        if error_response is not None:
            return error_response

        try:
            template = program.certificate_template
        except ProgramCertificateTemplate.DoesNotExist:
            return Response(
                {"detail": "Certificate settings were not configured."},
                status=status.HTTP_404_NOT_FOUND,
            )

        template.released_at = timezone.now()
        template.save(update_fields=["released_at", "datetime_updated"])
        return Response(ProgramCertificateTemplateSerializer(template).data)


class ProgramCertificateListView(CertificateTemplateAccessMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        program, error_response = self.get_program_or_response(request, pk)
        if error_response is not None:
            return error_response

        certificates = (
            IssuedCertificate.objects.filter(program=program)
            .exclude(status=IssuedCertificate.STATUS_REVOKED)
            .select_related("user", "pdf_file", "program_project", "program_project__project")
            .order_by("-generated_at", "-issued_at", "-id")
        )
        return Response(
            {
                "certificates": IssuedCertificateSerializer(certificates, many=True).data,
                "stats": CertificateGenerationStatsSerializer(
                    get_certificate_stats(program)
                ).data,
            }
        )


class ProgramCertificateDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, certificate_id):
        program = get_object_or_404(PartnerProgram, pk=pk)
        certificate = get_object_or_404(
            IssuedCertificate.objects.select_related(
                "program__certificate_template",
                "pdf_file",
                "user",
            ),
            program=program,
            certificate_id=certificate_id,
        )

        is_manager = bool(
            getattr(request.user, "is_staff", False)
            or getattr(request.user, "is_superuser", False)
            or program.is_manager(request.user)
        )
        is_owner = certificate.user_id == request.user.id
        if not is_manager and not is_owner:
            return Response(
                {"detail": "Insufficient permissions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if is_owner and not is_manager:
            try:
                template = program.certificate_template
            except ProgramCertificateTemplate.DoesNotExist:
                return Response(
                    {"detail": "Certificate settings were not configured."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if not is_certificate_released_for_participant(
                program=program,
                template=template,
            ):
                return Response(
                    {"detail": "Certificate is not available yet."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if not certificate.pdf_file_id:
            return Response(
                {"detail": "Certificate PDF is not available."},
                status=status.HTTP_404_NOT_FOUND,
            )

        content, filename, content_type = read_user_file_bytes(certificate.pdf_file)
        certificate.downloaded_at = timezone.now()
        certificate.save(update_fields=["downloaded_at"])

        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class MyProgramCertificateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        program = get_object_or_404(PartnerProgram, pk=pk)
        if not PartnerProgramUserProfile.objects.filter(
            partner_program=program,
            user=request.user,
        ).exists():
            return Response(
                {"detail": "User is not registered in this program."},
                status=status.HTTP_403_FORBIDDEN,
            )

        state = get_participant_certificate_state(program=program, user=request.user)
        certificate = state.get("certificate")
        payload = {
            "state": state.get("state"),
            "available_at": state.get("available_at"),
            "settings": state.get("settings"),
            "certificate": (
                IssuedCertificateSerializer(certificate).data if certificate else None
            ),
        }
        return Response(payload)


class PublicCertificateVerificationAPIView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request, certificate_uuid):
        parsed_uuid = parse_certificate_uuid(certificate_uuid)
        if parsed_uuid is None:
            return Response(
                {
                    "is_valid": False,
                    "detail": INVALID_CERTIFICATE_UUID_MESSAGE,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        certificate = get_public_certificate(parsed_uuid)
        if certificate is None:
            return Response(
                {
                    "is_valid": False,
                    "detail": CERTIFICATE_NOT_FOUND_MESSAGE,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(PublicCertificateVerificationSerializer(certificate).data)


class PublicCertificateVerificationPageView(View):
    def get(self, request, certificate_uuid):
        parsed_uuid = parse_certificate_uuid(certificate_uuid)
        if parsed_uuid is None:
            return self.render_error(
                request,
                certificate_uuid,
                INVALID_CERTIFICATE_UUID_MESSAGE,
                status.HTTP_400_BAD_REQUEST,
            )

        certificate = get_public_certificate(parsed_uuid)
        if certificate is None:
            return self.render_error(
                request,
                certificate_uuid,
                CERTIFICATE_NOT_FOUND_MESSAGE,
                status.HTTP_404_NOT_FOUND,
            )

        payload = PublicCertificateVerificationSerializer(certificate).data
        return render(
            request,
            "certificates/verify.html",
            {
                "is_valid": True,
                "certificate_uuid": certificate_uuid,
                "certificate": payload,
                "program_finished_display": self.format_datetime(
                    certificate.program.datetime_finished
                ),
                "certificate_issued_display": self.format_datetime(certificate.issued_at),
            },
            status=status.HTTP_200_OK,
        )

    def render_error(self, request, certificate_uuid, message, response_status):
        return render(
            request,
            "certificates/verify.html",
            {
                "is_valid": False,
                "certificate_uuid": certificate_uuid,
                "message": message,
            },
            status=response_status,
        )

    def format_datetime(self, value):
        if value is None:
            return ""
        return timezone.localtime(value).strftime("%d.%m.%Y")


class IssuedCertificateDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        if not (
            getattr(request.user, "is_staff", False)
            or getattr(request.user, "is_superuser", False)
        ):
            return Response(
                {"detail": "Admin permissions are required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        certificate = get_object_or_404(
            IssuedCertificate.objects.select_related("pdf_file"),
            pk=pk,
        )
        pdf_file = certificate.pdf_file
        if pdf_file:
            from files.service import CDN, get_default_storage

            CDN(storage=get_default_storage()).delete(pdf_file.link)
        certificate.delete()
        if pdf_file:
            pdf_file.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
