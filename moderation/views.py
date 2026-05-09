from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, DateTimeField, Max, Prefetch, Q
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.timezone import is_naive, make_aware
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import Pagination
from moderation.models import ModerationLog
from moderation.permissions import IsStaffModerator
from moderation.serializers import (
    ModerationDecisionSerializer,
    ModerationLogSerializer,
    ModerationProgramDetailSerializer,
    ModerationProgramListSerializer,
    ModerationVerificationDecisionSerializer,
    ModerationVerificationRequestSerializer,
    ModerationVerificationRevokeSerializer,
    RejectionReasonSerializer,
)
from moderation.services import (
    ModerationTransitionError,
    archive_program,
    approve_program,
    freeze_program_manually,
    get_rejection_reasons,
    reject_program,
    restore_program,
)
from partner_programs.models import PartnerProgram, PartnerProgramVerificationRequest
from partner_programs.verification_services import (
    VerificationTransitionError,
    approve_verification_request,
    get_verification_rejection_reasons,
    reject_verification_request,
    revoke_program_verification,
)


class ModerationProgramPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class ModerationProgramListView(generics.ListAPIView):
    serializer_class = ModerationProgramListSerializer
    permission_classes = [IsStaffModerator]
    pagination_class = ModerationProgramPagination

    allowed_statuses = {
        PartnerProgram.STATUS_DRAFT,
        PartnerProgram.STATUS_PENDING_MODERATION,
        PartnerProgram.STATUS_REJECTED,
        PartnerProgram.STATUS_PUBLISHED,
        PartnerProgram.STATUS_COMPLETED,
        PartnerProgram.STATUS_FROZEN,
        PartnerProgram.STATUS_ARCHIVED,
    }
    attention_statuses = {
        PartnerProgram.STATUS_PENDING_MODERATION,
        PartnerProgram.STATUS_REJECTED,
        PartnerProgram.STATUS_FROZEN,
    }
    ordering_map = {
        "created": "datetime_created",
        "-created": "-datetime_created",
        "updated": "datetime_updated",
        "-updated": "-datetime_updated",
        "name": "name",
        "-name": "-name",
        "submitted": "submitted_at_sort",
        "-submitted": "-submitted_at_sort",
        "submitted_at": "submitted_at_sort",
        "-submitted_at": "-submitted_at_sort",
        "decision": "decision_at_value",
        "-decision": "-decision_at_value",
        "decision_at": "decision_at_value",
        "-decision_at": "-decision_at_value",
    }

    def get_queryset(self):
        qs = self._base_queryset()

        status_param = self.request.query_params.get(
            "status",
            PartnerProgram.STATUS_PENDING_MODERATION,
        )
        if status_param == "all":
            qs = qs.filter(status__in=self.allowed_statuses)
        elif status_param == "attention":
            qs = qs.filter(status__in=self.attention_statuses)
        elif status_param in self.allowed_statuses:
            qs = qs.filter(status=status_param)
        else:
            status_param = PartnerProgram.STATUS_PENDING_MODERATION
            qs = qs.filter(status=status_param)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(tag__icontains=search)
                | Q(city__icontains=search)
                | Q(company__name__icontains=search)
                | Q(managers__email__icontains=search)
                | Q(managers__first_name__icontains=search)
                | Q(managers__last_name__icontains=search)
            ).distinct()

        qs = self._apply_date_filters(qs, status_param)

        frozen_from = self._parse_datetime_param("frozen_from")
        if frozen_from:
            qs = qs.filter(frozen_at__gte=frozen_from)

        frozen_to = self._parse_datetime_param("frozen_to")
        if frozen_to:
            qs = qs.filter(frozen_at__lte=frozen_to)

        requested_ordering = self.request.query_params.get("ordering")
        default_ordering = (
            "-decision" if status_param == PartnerProgram.STATUS_PUBLISHED else "-submitted"
        )
        ordering = self.ordering_map.get(
            requested_ordering or default_ordering,
            self.ordering_map[default_ordering],
        )
        return qs.order_by(ordering, "-id")

    def _base_queryset(self):
        return (
            PartnerProgram.objects.select_related("company")
            .prefetch_related("managers", "materials", "experts__user")
            .prefetch_related(
                Prefetch(
                    "moderation_logs",
                    queryset=ModerationLog.objects.select_related(
                        "author",
                        "program",
                    ).order_by("-datetime_created", "-id"),
                )
            )
            .annotate(
                submitted_at_value=Max(
                    "moderation_logs__datetime_created",
                    filter=Q(
                        moderation_logs__action__in=ModerationLog.SUBMISSION_ACTIONS
                    ),
                ),
                decision_at_value=Max(
                    "moderation_logs__datetime_created",
                    filter=Q(moderation_logs__action__in=ModerationLog.DECISION_ACTIONS),
                ),
                participants_count_value=Count("users", distinct=True),
            )
            .annotate(
                submitted_at_sort=Coalesce(
                    "submitted_at_value",
                    "datetime_updated",
                    "datetime_created",
                    output_field=DateTimeField(),
                )
            )
        )

    def _apply_date_filters(self, qs, status_param):
        if status_param == PartnerProgram.STATUS_PUBLISHED:
            date_from = (
                self._parse_datetime_param("decision_from")
                or self._parse_datetime_param("published_from")
                or self._parse_datetime_param("date_from")
            )
            date_to = (
                self._parse_datetime_param("decision_to")
                or self._parse_datetime_param("published_to")
                or self._parse_datetime_param("date_to")
            )
            if not date_from and not date_to:
                date_from = timezone.now() - timedelta(days=7)
            if date_from:
                qs = qs.filter(decision_at_value__gte=date_from)
            if date_to:
                qs = qs.filter(decision_at_value__lte=date_to)
            return qs

        date_from = (
            self._parse_datetime_param("submitted_from")
            or self._parse_datetime_param("date_from")
        )
        date_to = (
            self._parse_datetime_param("submitted_to")
            or self._parse_datetime_param("date_to")
        )
        if date_from:
            qs = qs.filter(submitted_at_sort__gte=date_from)
        if date_to:
            qs = qs.filter(submitted_at_sort__lte=date_to)
        return qs

    def _parse_datetime_param(self, name):
        raw_value = self.request.query_params.get(name)
        if not raw_value:
            return None
        return parse_datetime_or_date(raw_value)


class ModerationProgramDetailView(generics.RetrieveAPIView):
    serializer_class = ModerationProgramDetailSerializer
    permission_classes = [IsStaffModerator]
    queryset = (
        PartnerProgram.objects.select_related("company")
        .prefetch_related("managers", "materials", "experts__user")
        .prefetch_related(
            Prefetch(
                "moderation_logs",
                queryset=ModerationLog.objects.select_related(
                    "author",
                    "program",
                ).order_by("-datetime_created", "-id"),
            )
        )
        .annotate(
            submitted_at_value=Max(
                "moderation_logs__datetime_created",
                filter=Q(moderation_logs__action__in=ModerationLog.SUBMISSION_ACTIONS),
            ),
            decision_at_value=Max(
                "moderation_logs__datetime_created",
                filter=Q(moderation_logs__action__in=ModerationLog.DECISION_ACTIONS),
            ),
            participants_count_value=Count("users", distinct=True),
        )
        .annotate(
            submitted_at_sort=Coalesce(
                "submitted_at_value",
                "datetime_updated",
                "datetime_created",
                output_field=DateTimeField(),
            )
        )
    )


class ModerationDecisionView(APIView):
    permission_classes = [IsStaffModerator]

    def post(self, request, pk):
        program = get_object_or_404(PartnerProgram, pk=pk)
        serializer = ModerationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        try:
            if data["decision"] == "approve":
                log = approve_program(
                    program,
                    author=request.user,
                    comment=data.get("comment", ""),
                )
            else:
                log = reject_program(
                    program,
                    author=request.user,
                    comment=data["comment"],
                    rejection_reason=data["reason_code"],
                    sections_to_fix=data.get("sections_to_fix", []),
                )
        except ModerationTransitionError as exc:
            return transition_error_response(
                "Program cannot be decided from status",
                exc.current_status,
            )
        except DjangoValidationError as exc:
            return validation_error_response(exc)

        program.refresh_from_db()
        return moderation_action_response(log, program)


class ModerationProgramFreezeView(APIView):
    permission_classes = [IsStaffModerator]

    def post(self, request, pk):
        program = get_object_or_404(PartnerProgram, pk=pk)
        try:
            log = freeze_program_manually(
                program,
                author=request.user,
                comment=request.data.get("comment", ""),
            )
        except ModerationTransitionError as exc:
            return transition_error_response(
                "Program cannot be frozen from status",
                exc.current_status,
            )
        except DjangoValidationError as exc:
            return validation_error_response(exc)

        program.refresh_from_db()
        return moderation_action_response(log, program)


class ModerationProgramRestoreView(APIView):
    permission_classes = [IsStaffModerator]

    def post(self, request, pk):
        program = get_object_or_404(PartnerProgram, pk=pk)
        try:
            log = restore_program(
                program,
                author=request.user,
                comment=request.data.get("comment", ""),
            )
        except ModerationTransitionError as exc:
            return transition_error_response(
                "Program cannot be restored from status",
                exc.current_status,
            )
        except DjangoValidationError as exc:
            return validation_error_response(exc)

        program.refresh_from_db()
        return moderation_action_response(log, program)


class ModerationProgramArchiveView(APIView):
    permission_classes = [IsStaffModerator]

    def post(self, request, pk):
        program = get_object_or_404(PartnerProgram, pk=pk)
        try:
            log = archive_program(
                program,
                author=request.user,
                comment=request.data.get("comment", ""),
            )
        except ModerationTransitionError as exc:
            return transition_error_response(
                "Program cannot be archived from status",
                exc.current_status,
            )
        except DjangoValidationError as exc:
            return validation_error_response(exc)

        program.refresh_from_db()
        return moderation_action_response(log, program)


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

        author_id = self.request.query_params.get("author_id")
        if author_id:
            qs = qs.filter(author_id=author_id)

        date_from = self._parse_datetime_param("date_from")
        if date_from:
            qs = qs.filter(datetime_created__gte=date_from)

        date_to = self._parse_datetime_param("date_to")
        if date_to:
            qs = qs.filter(datetime_created__lte=date_to)

        return qs.order_by("-datetime_created", "-id")

    def _parse_datetime_param(self, name):
        raw_value = self.request.query_params.get(name)
        if not raw_value:
            return None
        return parse_datetime_or_date(raw_value)


class RejectionReasonListView(APIView):
    permission_classes = [IsStaffModerator]

    def get(self, request):
        return Response(
            RejectionReasonSerializer(get_rejection_reasons(), many=True).data,
            status=status.HTTP_200_OK,
        )


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


def parse_datetime_or_date(raw_value):
    value = parse_datetime(raw_value)
    if value is None:
        parsed_date = parse_date(raw_value)
        if parsed_date is None:
            return None
        value = datetime.combine(parsed_date, time.min)
    if is_naive(value):
        value = make_aware(value)
    return value


def moderation_action_response(log: ModerationLog, program: PartnerProgram) -> Response:
    return Response(
        {
            "log": ModerationLogSerializer(log).data,
            "program": {
                "id": program.id,
                "status": program.status,
                "draft": program.draft,
                "frozen_at": program.frozen_at,
            },
        },
        status=status.HTTP_200_OK,
    )
