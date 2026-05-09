from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from .constants import VERBOSE_TYPES
from .constants import NumericTypes

from partner_programs.models import PartnerProgram, PartnerProgramProject
from projects.models import Project
from .validators import ProjectScoreValidator

User = get_user_model()


class Criteria(models.Model):
    """
    Criteria model

    Attributes:
        name:  A CharField name of the criteria
        description: A TextField description of criteria
        type: A CharField choice between "str", "int", "bool" and "float"
        min_value: Optional FloatField for numeric values
        max_value: Optional FloatField for numeric values
        partner_program: A ForeignKey connection to PartnerProgram model

    """

    name = models.CharField(verbose_name="Название", max_length=50)
    description = models.TextField(verbose_name="Описание", null=True, blank=True)
    type = models.CharField(verbose_name="Тип", max_length=8, choices=VERBOSE_TYPES)

    min_value = models.FloatField(
        verbose_name="Минимально допустимое числовое значение",
        help_text="(если есть)",
        null=True,
        blank=True,
    )
    max_value = models.FloatField(
        verbose_name="Максимально допустимое числовое значение",
        help_text="(если есть)",
        null=True,
        blank=True,
    )
    weight = models.PositiveSmallIntegerField(
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name="Criterion weight, %",
    )
    partner_program = models.ForeignKey(
        PartnerProgram,
        on_delete=models.CASCADE,
        related_name="criterias",
    )

    def __str__(self):
        return f"Criteria<{self.id}> - {self.name} {self.partner_program.name}"

    class Meta:
        verbose_name = "Критерий оценки проекта"
        verbose_name_plural = "Критерии оценки проектов"


class ProjectScore(models.Model):
    """
    ProjectScore model

    Attributes:
        criteria:  A ForeignKey connection to Criteria model
        user:  A ForeignKey connection to User model

        value: CharField for value


    """

    criteria = models.ForeignKey(
        Criteria, on_delete=models.CASCADE, related_name="scores"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scores")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="scores")

    value = models.CharField(
        verbose_name="Значение", max_length=50, null=True, blank=True
    )

    def __str__(self):
        return f"ProjectScore<{self.id}> - {self.criteria.name}"

    def save(self, *args, **kwargs):
        data_to_validate = {
            "criteria_type": self.criteria.type,
            "value": self.value,
            "criteria_min_value": self.criteria.min_value,
            "criteria_max_value": self.criteria.max_value,
        }
        ProjectScoreValidator.validate(**data_to_validate)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Оценка проекта"
        verbose_name_plural = "Оценки проектов"
        unique_together = ("criteria", "user", "project")


class ProjectEvaluation(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
    )

    program_project = models.ForeignKey(
        PartnerProgramProject,
        on_delete=models.CASCADE,
        related_name="evaluations",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="project_evaluations",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    comment = models.TextField(blank=True)
    total_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Project evaluation"
        verbose_name_plural = "Project evaluations"
        unique_together = ("program_project", "user")
        indexes = [
            models.Index(fields=["program_project", "user"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return (
            f"ProjectEvaluation<{self.id}> "
            f"program_project={self.program_project_id} user={self.user_id}"
        )

    @property
    def is_submitted(self) -> bool:
        return self.status == self.STATUS_SUBMITTED

    def mark_submitted(self):
        self.status = self.STATUS_SUBMITTED
        self.submitted_at = timezone.now()

    def calculate_total_score(self, *, require_complete: bool = False) -> Decimal | None:
        program = self.program_project.partner_program
        numeric_criteria = list(
            Criteria.objects.filter(
                partner_program=program,
                type__in=NumericTypes,
            ).order_by("id")
        )

        if not numeric_criteria:
            if require_complete:
                raise ValidationError(
                    {"criteria": "No numeric criteria are configured for scoring."}
                )
            return None

        scores_by_criterion_id = {
            score.criterion_id: score for score in self.evaluation_scores.all()
        }

        weighted_sum = Decimal("0")
        weight_sum = Decimal("0")

        for criterion in numeric_criteria:
            score = scores_by_criterion_id.get(criterion.id)
            if score is None or score.value in (None, ""):
                if require_complete:
                    raise ValidationError(
                        {
                            "scores": (
                                "All numeric criteria must be filled before submission."
                            )
                        }
                    )
                continue

            if criterion.max_value is None or criterion.max_value <= 0:
                if require_complete:
                    raise ValidationError(
                        {
                            "criteria": (
                                "Numeric criteria must have a positive max_value."
                            )
                        }
                    )
                return None

            try:
                value = Decimal(str(score.value))
                max_value = Decimal(str(criterion.max_value))
                weight = Decimal(str(criterion.weight or 0))
            except (InvalidOperation, TypeError, ValueError) as exc:
                if require_complete:
                    raise ValidationError({"scores": str(exc)})
                return None

            weighted_sum += (value / max_value * Decimal("10")) * weight
            weight_sum += weight

        if weight_sum <= 0:
            if require_complete:
                raise ValidationError(
                    {
                        "criteria": (
                            "The sum of numeric criteria weights must be greater than 0."
                        )
                    }
                )
            return None

        return (weighted_sum / weight_sum).quantize(Decimal("0.01"))


class ProjectEvaluationScore(models.Model):
    evaluation = models.ForeignKey(
        ProjectEvaluation,
        on_delete=models.CASCADE,
        related_name="evaluation_scores",
    )
    criterion = models.ForeignKey(
        Criteria,
        on_delete=models.CASCADE,
        related_name="evaluation_scores",
    )
    value = models.CharField(max_length=50, null=True, blank=True)
    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Project evaluation score"
        verbose_name_plural = "Project evaluation scores"
        unique_together = ("evaluation", "criterion")
        indexes = [
            models.Index(fields=["evaluation", "criterion"]),
        ]

    def __str__(self):
        return f"ProjectEvaluationScore<{self.id}> - {self.criterion_id}"

    def clean(self):
        errors = {}

        if (
            self.evaluation_id
            and self.criterion_id
            and self.criterion.partner_program_id
            != self.evaluation.program_project.partner_program_id
        ):
            errors["criterion"] = "Criterion does not belong to this program."

        if self.criterion_id and self.value not in (None, ""):
            data_to_validate = {
                "criteria_type": self.criterion.type,
                "value": self.value,
                "criteria_min_value": self.criterion.min_value,
                "criteria_max_value": self.criterion.max_value,
            }
            try:
                ProjectScoreValidator.validate(**data_to_validate)
            except (TypeError, ValueError) as exc:
                errors["value"] = str(exc)

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ProjectExpertAssignment(models.Model):
    partner_program = models.ForeignKey(
        PartnerProgram,
        on_delete=models.CASCADE,
        related_name="project_expert_assignments",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="expert_assignments",
    )
    expert = models.ForeignKey(
        "users.Expert",
        on_delete=models.CASCADE,
        related_name="project_assignments",
    )
    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Назначение проекта эксперту"
        verbose_name_plural = "Назначения проектов экспертам"
        unique_together = ("partner_program", "project", "expert")
        indexes = [
            models.Index(fields=["partner_program", "project"]),
            models.Index(fields=["partner_program", "expert"]),
        ]

    def __str__(self):
        return (
            f"Assignment<{self.id}> program={self.partner_program_id} "
            f"project={self.project_id} expert={self.expert_id}"
        )

    def has_scores(self) -> bool:
        legacy_scores_exist = ProjectScore.objects.filter(
            project_id=self.project_id,
            user_id=self.expert.user_id,
            criteria__partner_program_id=self.partner_program_id,
        ).exists()
        evaluation_exists = ProjectEvaluation.objects.filter(
            program_project__partner_program_id=self.partner_program_id,
            program_project__project_id=self.project_id,
            user_id=self.expert.user_id,
        ).exists()
        return legacy_scores_exist or evaluation_exists

    def clean(self):
        errors = {}

        if self.expert_id and self.partner_program_id and not self.expert.programs.filter(
            id=self.partner_program_id
        ).exists():
            errors["expert"] = "Эксперт не состоит в указанной программе."

        if self.project_id and self.partner_program_id and not PartnerProgramProject.objects.filter(
            partner_program_id=self.partner_program_id,
            project_id=self.project_id,
        ).exists():
            errors["project"] = "Проект не привязан к указанной программе."

        if self.partner_program_id and self.project_id:
            max_rates = self.partner_program.max_project_rates
            if max_rates:
                assignments_qs = ProjectExpertAssignment.objects.filter(
                    partner_program_id=self.partner_program_id,
                    project_id=self.project_id,
                )
                if self.pk:
                    assignments_qs = assignments_qs.exclude(pk=self.pk)
                if assignments_qs.count() >= max_rates:
                    errors["partner_program"] = (
                        "Достигнуто максимальное количество назначенных экспертов "
                        "для этого проекта в программе."
                    )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.has_scores():
            raise ValidationError(
                "Нельзя удалить назначение: эксперт уже оценил этот проект."
            )
        return super().delete(*args, **kwargs)
