from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Prefetch, Q, QuerySet
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_filters import rest_framework as filters

from partner_programs.models import PartnerProgram, PartnerProgramProject
from partner_programs.serializers import ProgramProjectFilterRequestSerializer
from partner_programs.utils import filter_program_projects_by_field_name
from projects.models import Collaborator, Project, ProjectLink
from projects.filters import ProjectFilter
from project_rates.models import (
    Criteria,
    ProjectEvaluation,
    ProjectEvaluationScore,
    ProjectExpertAssignment,
    ProjectScore,
)
from project_rates.pagination import RateProjectsPagination
from project_rates.serializers import (
    ProjectEvaluationSaveSerializer,
    ProjectListForRateSerializer,
    ProjectScoreCreateSerializer,
    ProjectSubmissionDetailSerializer,
    ProjectSubmissionListSerializer,
)
from users.models import Expert
from users.permissions import IsExpert, IsExpertPost
from vacancy.mapping import ProjectRatedParams, MessageTypeEnum
from vacancy.tasks import send_email

User = get_user_model()


class RateProject(generics.CreateAPIView):
    serializer_class = ProjectScoreCreateSerializer
    permission_classes = [IsExpertPost]

    def get_needed_data(self) -> tuple[dict, list[int], PartnerProgram]:
        data = self.request.data
        user_id = self.request.user.id
        project_id = self.kwargs.get("project_id")

        criteria_to_get = [
            criterion["criterion_id"] for criterion in data
        ]  # is needed for validation later

        criteria_qs = Criteria.objects.filter(id__in=criteria_to_get).select_related(
            "partner_program"
        )
        partner_program_ids = (
            criteria_qs.values_list("partner_program_id", flat=True).distinct()
        )
        if not criteria_qs.exists():
            raise ValueError("Criteria not found")
        if partner_program_ids.count() != 1:
            raise ValueError("All criteria must belong to the same program")
        program = criteria_qs.first().partner_program

        Expert.objects.get(user__id=user_id, programs=program)

        for criterion in data:
            criterion["user"] = user_id
            criterion["project"] = project_id
            criterion["criteria"] = criterion.pop("criterion_id")

        if not PartnerProgramProject.objects.filter(
            partner_program=program, project_id=project_id
        ).exists():
            raise ValueError("Project is not linked to the program")

        if program.is_distributed_evaluation and not ProjectExpertAssignment.objects.filter(
            partner_program=program,
            project_id=project_id,
            expert__user_id=user_id,
        ).exists():
            raise ValueError("you are not assigned to rate this project")

        return data, criteria_to_get, program

    def create(self, request, *args, **kwargs) -> Response:
        try:
            data, criteria_to_get, program = self.get_needed_data()
            project_id = data[0]["project"]
            user_id = request.user.id

            serializer = ProjectScoreCreateSerializer(
                data=data, criteria_to_get=criteria_to_get, many=True
            )
            serializer.is_valid(raise_exception=True)

            scores_qs = ProjectScore.objects.filter(
                project_id=project_id, criteria__partner_program=program
            )
            user_has_scores = scores_qs.filter(user_id=user_id).exists()

            if program.max_project_rates:
                distinct_raters = scores_qs.values("user_id").distinct().count()
                if not user_has_scores and distinct_raters >= program.max_project_rates:
                    return Response(
                        {
                            "error": "max project rates reached for this program",
                            "max_project_rates": program.max_project_rates,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            with transaction.atomic():
                ProjectScore.objects.bulk_create(
                    [ProjectScore(**item) for item in serializer.validated_data],
                    update_conflicts=True,
                    update_fields=["value"],
                    unique_fields=["criteria", "user", "project"],
                )

            project = Project.objects.select_related("leader").get(id=project_id)

            send_email.delay(
                ProjectRatedParams(
                    message_type=MessageTypeEnum.PROJECT_RATED.value,
                    user_id=project.leader.id,
                    project_name=project.name,
                    project_id=project.id,
                    schema_id=2,
                    program_name=program.name,
                )
            )

            return Response({"success": True}, status=status.HTTP_201_CREATED)
        except Expert.DoesNotExist:
            return Response(
                {"error": "you have no permission to rate this program"},
                status=status.HTTP_403_FORBIDDEN,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProjectListForRate(generics.ListAPIView):
    permission_classes = [IsExpert]
    serializer_class = ProjectListForRateSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = ProjectFilter
    pagination_class = RateProjectsPagination

    def post(self, request, *args, **kwargs):
        """Allow POST with filters in JSON body."""
        return self.list(request, *args, **kwargs)

    def _get_program(self) -> PartnerProgram:
        return PartnerProgram.objects.get(pk=self.kwargs.get("program_id"))

    def _get_filters(self) -> dict:
        """
        Accept filters from JSON body to mirror /partner_programs/<id>/projects/filter/:
        {"filters": {"case": ["Кейс 1"]}}
        """
        if self.request.method != "POST":
            return {}
        data = getattr(self.request, "data", None)
        body_filters = data.get("filters") if isinstance(data, dict) else {}
        return body_filters if isinstance(body_filters, dict) else {}

    def get_queryset(self) -> QuerySet[Project]:
        program = self._get_program()

        filters_serializer = ProgramProjectFilterRequestSerializer(
            data={"filters": self._get_filters()}
        )
        filters_serializer.is_valid(raise_exception=True)
        field_filters = filters_serializer.validated_data.get("filters", {})

        try:
            program_projects_qs = filter_program_projects_by_field_name(
                program, field_filters
            )
        except ValueError as e:
            raise ValidationError({"filters": str(e)})

        project_ids = program_projects_qs.values_list("project_id", flat=True)

        scores_prefetch = Prefetch(
            "scores",
            queryset=ProjectScore.objects.filter(
                criteria__partner_program=program
            ).select_related("user"),
            to_attr="_program_scores",
        )

        projects_qs = Project.objects.filter(draft=False, id__in=project_ids)
        if program.is_distributed_evaluation:
            projects_qs = projects_qs.filter(
                expert_assignments__partner_program=program,
                expert_assignments__expert__user=self.request.user,
            )

        return (
            projects_qs
            .annotate(
                rated_count=Count(
                    "scores__user",
                    filter=Q(scores__criteria__partner_program=program),
                    distinct=True,
                )
            )
            .prefetch_related(scores_prefetch)
            .distinct()
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["program_max_rates"] = self._get_program().max_project_rates
        return context


class ExpertSubmissionAccessMixin:
    permission_classes = [IsAuthenticated]
    pagination_class = RateProjectsPagination

    def get_program(self) -> PartnerProgram:
        try:
            return PartnerProgram.objects.get(pk=self.kwargs["program_id"])
        except PartnerProgram.DoesNotExist as exc:
            raise NotFound("Program not found.") from exc

    def is_staff_request(self) -> bool:
        user = self.request.user
        return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))

    def is_program_manager_request(self, program: PartnerProgram) -> bool:
        user = self.request.user
        return bool(user and user.is_authenticated and program.is_manager(user))

    def ensure_program_access(self, program: PartnerProgram) -> None:
        user = self.request.user
        if self.is_staff_request() or self.is_program_manager_request(program):
            return
        if not Expert.objects.filter(user=user, programs=program).exists():
            raise PermissionDenied("You don't have permission to evaluate this program.")

    def get_accessible_program_projects(self, program: PartnerProgram):
        self.ensure_program_access(program)

        current_user_evaluations = ProjectEvaluation.objects.filter(
            user=self.request.user
        ).prefetch_related("evaluation_scores")

        queryset = (
            PartnerProgramProject.objects.filter(
                partner_program=program,
                submitted=True,
            )
            .select_related("partner_program", "project", "project__leader")
            .prefetch_related(
                Prefetch(
                    "project__collaborator_set",
                    queryset=Collaborator.objects.select_related("user").order_by("id"),
                    to_attr="_prefetched_collaborators",
                ),
                Prefetch(
                    "project__links",
                    queryset=ProjectLink.objects.order_by("id"),
                    to_attr="_prefetched_links",
                ),
                Prefetch(
                    "evaluations",
                    queryset=current_user_evaluations,
                    to_attr="_current_user_evaluations",
                ),
            )
        )

        if (
            program.is_distributed_evaluation
            and not self.is_staff_request()
            and not self.is_program_manager_request(program)
        ):
            queryset = queryset.filter(
                project__expert_assignments__partner_program=program,
                project__expert_assignments__expert__user=self.request.user,
            )

        return queryset.distinct()

    def get_program_project(self, program: PartnerProgram) -> PartnerProgramProject:
        program_project_id = self.kwargs["program_project_id"]
        try:
            return self.get_accessible_program_projects(program).get(pk=program_project_id)
        except PartnerProgramProject.DoesNotExist as exc:
            raise NotFound("Submitted project is not available.") from exc

    def get_counters(self, queryset):
        assigned = queryset.count()
        evaluated = (
            queryset.filter(
                evaluations__user=self.request.user,
                evaluations__status=ProjectEvaluation.STATUS_SUBMITTED,
            )
            .distinct()
            .count()
        )
        return {
            "assigned": assigned,
            "evaluated": evaluated,
            "remaining": max(assigned - evaluated, 0),
        }

    def get_program_meta(self, program: PartnerProgram):
        return {
            "id": program.id,
            "name": program.name,
            "stage": "Expert evaluation",
            "datetime_evaluation_ends": program.datetime_evaluation_ends,
            "is_distributed_evaluation": program.is_distributed_evaluation,
            "participation_format": program.participation_format,
        }

    def filter_queryset_for_request(self, queryset):
        query = (self.request.query_params.get("search") or "").strip()
        if query:
            queryset = queryset.filter(
                Q(project__name__icontains=query)
                | Q(project__leader__first_name__icontains=query)
                | Q(project__leader__last_name__icontains=query)
                | Q(project__leader__email__icontains=query)
                | Q(project__collaborator_set__user__first_name__icontains=query)
                | Q(project__collaborator_set__user__last_name__icontains=query)
                | Q(project__collaborator_set__user__email__icontains=query)
            )

        evaluation_status = self.request.query_params.get("status")
        if evaluation_status in ("not_started", "not_evaluated", "unrated"):
            queryset = queryset.exclude(evaluations__user=self.request.user)
        elif evaluation_status in (
            ProjectEvaluation.STATUS_DRAFT,
            ProjectEvaluation.STATUS_SUBMITTED,
        ):
            queryset = queryset.filter(
                evaluations__user=self.request.user,
                evaluations__status=evaluation_status,
            )

        return queryset.distinct()


class ProjectSubmissionListView(ExpertSubmissionAccessMixin, generics.GenericAPIView):
    serializer_class = ProjectSubmissionListSerializer

    def get(self, request, *args, **kwargs):
        program = self.get_program()
        base_queryset = self.get_accessible_program_projects(program)
        counters = self.get_counters(base_queryset)
        queryset = self.filter_queryset_for_request(base_queryset).order_by(
            "-datetime_submitted", "-id"
        )

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        response = self.get_paginated_response(serializer.data)
        response.data["program"] = self.get_program_meta(program)
        response.data["counters"] = counters
        return response


class ExpertEvaluationProgramListView(ExpertSubmissionAccessMixin, generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        summaries = []

        for program in self.get_programs_for_user():
            base_queryset = self.get_accessible_program_projects(program)
            counters = self.get_counters(base_queryset)

            if counters["assigned"] <= 0 and not self.is_staff_request():
                continue

            summaries.append(
                {
                    "id": program.id,
                    "name": program.name,
                    "evaluation_deadline": program.datetime_evaluation_ends,
                    "assigned": counters["assigned"],
                    "evaluated": counters["evaluated"],
                    "remaining": counters["remaining"],
                    "stage": "Expert evaluation",
                    "stage_status": self.get_stage_status(program, counters),
                    "is_distributed_evaluation": program.is_distributed_evaluation,
                }
            )

        return Response(summaries)

    def get_programs_for_user(self):
        queryset = PartnerProgram.objects.filter(program_projects__submitted=True)

        if self.is_staff_request():
            return queryset.distinct().order_by("datetime_evaluation_ends", "id")

        managed_programs = queryset.filter(managers=self.request.user)

        expert = Expert.objects.filter(user=self.request.user).first()
        if not expert:
            return managed_programs.distinct().order_by("datetime_evaluation_ends", "id")

        expert_programs = expert.programs.filter(program_projects__submitted=True)
        return (
            (managed_programs | expert_programs)
            .distinct()
            .order_by("datetime_evaluation_ends", "id")
        )

    def get_stage_status(self, program: PartnerProgram, counters: dict) -> str:
        deadline = program.datetime_evaluation_ends

        if deadline and deadline < timezone.now():
            return "Deadline passed"

        if counters["assigned"] > 0 and counters["remaining"] == 0:
            return "All projects evaluated"

        return "Evaluation in progress"


class ProjectSubmissionDetailView(ExpertSubmissionAccessMixin, generics.GenericAPIView):
    serializer_class = ProjectSubmissionDetailSerializer

    def get(self, request, *args, **kwargs):
        program = self.get_program()
        program_project = self.get_program_project(program)
        serializer = self.get_serializer(program_project)
        return Response(serializer.data)


class ProjectEvaluationSaveMixin(ExpertSubmissionAccessMixin, generics.GenericAPIView):
    serializer_class = ProjectSubmissionDetailSerializer

    def save_evaluation(self, request, *, submit: bool):
        program = self.get_program()
        program_project = self.get_program_project(program)

        payload_serializer = ProjectEvaluationSaveSerializer(data=request.data)
        payload_serializer.is_valid(raise_exception=True)
        payload = payload_serializer.validated_data

        evaluation, _ = ProjectEvaluation.objects.get_or_create(
            program_project=program_project,
            user=request.user,
            defaults={"status": ProjectEvaluation.STATUS_DRAFT},
        )

        if evaluation.is_submitted:
            raise ValidationError(
                {"evaluation": "Submitted evaluation cannot be changed."}
            )

        with transaction.atomic():
            if "comment" in payload:
                evaluation.comment = payload.get("comment") or ""
                evaluation.save(update_fields=["comment", "datetime_updated"])

            self.save_scores(
                evaluation=evaluation,
                program=program,
                scores=payload.get("scores", []),
                submit=submit,
            )

            evaluation = ProjectEvaluation.objects.prefetch_related(
                "evaluation_scores"
            ).get(pk=evaluation.pk)
            try:
                evaluation.total_score = evaluation.calculate_total_score(
                    require_complete=submit
                )
            except DjangoValidationError as exc:
                error_detail = getattr(exc, "message_dict", None) or exc.messages
                raise ValidationError(error_detail) from exc

            update_fields = ["total_score", "datetime_updated"]
            if submit:
                evaluation.mark_submitted()
                update_fields.extend(["status", "submitted_at"])
            evaluation.save(update_fields=update_fields)

        program_project = self.get_program_project(program)
        return Response(
            ProjectSubmissionDetailSerializer(
                program_project,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_200_OK,
        )

    def save_scores(self, *, evaluation, program, scores, submit: bool):
        if not scores:
            return

        criteria_ids = [item["criterion_id"] for item in scores]
        criteria_by_id = {
            criterion.id: criterion
            for criterion in Criteria.objects.filter(
                id__in=criteria_ids,
                partner_program=program,
            )
        }
        missing_ids = sorted(set(criteria_ids) - set(criteria_by_id))
        if missing_ids:
            raise ValidationError(
                {"scores": f"Criteria do not belong to this program: {missing_ids}"}
            )

        for item in scores:
            criterion = criteria_by_id[item["criterion_id"]]
            value = item.get("value")

            if value in (None, "") and criterion.type in ("int", "float") and not submit:
                ProjectEvaluationScore.objects.filter(
                    evaluation=evaluation,
                    criterion=criterion,
                ).delete()
                continue

            if submit and value in (None, "") and criterion.type in ("int", "float"):
                raise ValidationError(
                    {
                        "scores": (
                            "All numeric criteria must be filled before submission."
                        )
                    }
                )

            score, _ = ProjectEvaluationScore.objects.get_or_create(
                evaluation=evaluation,
                criterion=criterion,
            )
            if criterion.type == "bool" and isinstance(value, str):
                normalized_bool = value.strip().lower()
                if normalized_bool in ("true", "false"):
                    value = normalized_bool == "true"
            score.value = None if value is None else str(value)
            try:
                score.save()
            except Exception as exc:
                raise ValidationError({"scores": str(exc)}) from exc


class ProjectEvaluationDraftView(ProjectEvaluationSaveMixin):
    def put(self, request, *args, **kwargs):
        return self.save_evaluation(request, submit=False)


class ProjectEvaluationSubmitView(ProjectEvaluationSaveMixin):
    def post(self, request, *args, **kwargs):
        return self.save_evaluation(request, submit=True)
