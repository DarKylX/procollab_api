from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import Pagination
from moderation.models import ModerationLog
from moderation.permissions import IsStaffModerator
from moderation.serializers import (
    ModerationLogSerializer,
    ModerationVerificationDecisionSerializer,
    ModerationVerificationRequestSerializer,
    ModerationVerificationRevokeSerializer,
    RejectionReasonSerializer,
)
from partner_programs.models import PartnerProgram, PartnerProgramVerificationRequest
from partner_programs.verification_services import (
    VerificationTransitionError,
    approve_verification_request,
    get_verification_rejection_reasons,
    reject_verification_request,
    revoke_program_verification,
)


class ModerationLogListView(generics.ListAPIView):
    serializer_class = ModerationLogSerializer
    permission_classes = [IsStaffModerator]
    pagination_class = Pagination

    def get_queryset(self):
        qs = ModerationLog.objects.select_related("program", "author")

        action = self.request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)

        program_id = self.request.query_params.get("program_id")
        if program_id:
            qs = qs.filter(program_id=program_id)

        return qs.order_by("-datetime_created", "-id")


class VerificationRejectionReasonListView(APIView):
    permission_classes = [IsStaffModerator]

    def get(self, request):
        return Response(
            RejectionReasonSerializer(
                get_verification_rejection_reasons(),
                many=True,
            ).data,
            status=status.HTTP_200_OK,
        )


class ModerationVerificationRequestListView(generics.ListAPIView):
    serializer_class = ModerationVerificationRequestSerializer
    permission_classes = [IsStaffModerator]
    pagination_class = Pagination

    allowed_statuses = {"pending", "approved", "rejected"}
    ordering_map = {
        "submitted": "submitted_at",
        "-submitted": "-submitted_at",
        "decided": "decided_at",
        "-decided": "-decided_at",
    }

    def get_queryset(self):
        qs = PartnerProgramVerificationRequest.objects.select_related(
            "program",
            "company",
            "initiator",
            "decided_by",
        ).prefetch_related("documents")

        status_param = self.request.query_params.get("status")
        if status_param in self.allowed_statuses:
            qs = qs.filter(status=status_param)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(company__name__icontains=search)
                | Q(company__inn__icontains=search)
                | Q(company_name__icontains=search)
                | Q(inn__icontains=search)
                | Q(program__name__icontains=search)
                | Q(program__tag__icontains=search)
            )

        ordering = self.ordering_map.get(
            self.request.query_params.get("ordering", "-submitted"),
            "-submitted_at",
        )
        return qs.order_by(ordering, "-id")


class ModerationVerificationRequestDetailView(generics.RetrieveAPIView):
    serializer_class = ModerationVerificationRequestSerializer
    permission_classes = [IsStaffModerator]
    queryset = (
        PartnerProgramVerificationRequest.objects.select_related(
            "program",
            "company",
            "initiator",
            "decided_by",
        )
        .prefetch_related("documents")
        .all()
    )


class ModerationVerificationDecisionView(APIView):
    permission_classes = [IsStaffModerator]

    def post(self, request, pk):
        verification_request = get_object_or_404(
            PartnerProgramVerificationRequest.objects.select_related(
                "program",
                "company",
                "initiator",
            ).prefetch_related("documents"),
            pk=pk,
        )
        serializer = ModerationVerificationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            if data["decision"] == "approve":
                log = approve_verification_request(
                    verification_request=verification_request,
                    author=request.user,
                    comment=data.get("comment", ""),
                )
            else:
                log = reject_verification_request(
                    verification_request=verification_request,
                    author=request.user,
                    comment=data["comment"],
                    rejection_reason=data["rejection_reason"],
                )
        except VerificationTransitionError as exc:
            return transition_error_response(
                "Verification request cannot be decided from status",
                exc.current_status,
            )
        except DjangoValidationError as exc:
            return validation_error_response(exc)

        verification_request.refresh_from_db()
        verification_request.program.refresh_from_db()
        return Response(
            {
                "request": ModerationVerificationRequestSerializer(
                    verification_request
                ).data,
                "log": ModerationLogSerializer(log).data,
                "program": {
                    "id": verification_request.program_id,
                    "status": verification_request.program.status,
                    "verification_status": verification_request.program.verification_status,
                    "company_id": verification_request.program.company_id,
                },
            },
            status=status.HTTP_200_OK,
        )


class ModerationVerificationRevokeView(APIView):
    permission_classes = [IsStaffModerator]

    def post(self, request, pk):
        program = get_object_or_404(PartnerProgram, pk=pk)
        serializer = ModerationVerificationRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            log = revoke_program_verification(
                program=program,
                author=request.user,
                comment=serializer.validated_data["comment"],
            )
        except VerificationTransitionError as exc:
            return transition_error_response(
                "Verification cannot be revoked from status",
                exc.current_status,
            )
        except DjangoValidationError as exc:
            return validation_error_response(exc)

        program.refresh_from_db()
        return Response(
            {
                "log": ModerationLogSerializer(log).data,
                "program": {
                    "id": program.id,
                    "verification_status": program.verification_status,
                    "company_id": program.company_id,
                },
            },
            status=status.HTTP_200_OK,
        )


def transition_error_response(prefix: str, current_status: str) -> Response:
    return Response(
        {
            "detail": f"{prefix} {current_status}",
            "current_status": current_status,
        },
        status=status.HTTP_409_CONFLICT,
    )


def validation_error_response(exc: DjangoValidationError) -> Response:
    return Response(
        exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages},
        status=status.HTTP_400_BAD_REQUEST,
    )
