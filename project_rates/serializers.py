from rest_framework import serializers

from core.services import get_views_count
from partner_programs.models import PartnerProgramProject
from projects.models import Project
from .models import Criteria, ProjectEvaluation, ProjectEvaluationScore, ProjectScore
from .typing import CriteriasResponse, ProjectScoresResponse
from .validators import ProjectScoreValidator
from users.models import CustomUser, Expert


class ProjectScoreCreateSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        self.criteria_to_get = kwargs.pop("criteria_to_get", None)
        super(ProjectScoreCreateSerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = ProjectScore
        fields = ["criteria", "user", "project", "value"]
        validators = []

    def get_queryset(self):
        return self.Meta.model.objects.filter(
            criteria__id__in=self.criteria_to_get
        ).select_related("criteria", "project", "user")

    def validate(self, data):
        criteria = data["criteria"]
        data_to_validate = {
            "criteria_type": criteria.type,
            "value": data.get("value"),
            "criteria_min_value": criteria.min_value,
            "criteria_max_value": criteria.max_value,
        }
        ProjectScoreValidator.validate(**data_to_validate)
        return data


class CriteriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Criteria
        exclude = ["partner_program"]


class ProgramCriteriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Criteria
        fields = [
            "id",
            "name",
            "description",
            "type",
            "min_value",
            "max_value",
            "weight",
        ]

    def validate(self, attrs):
        min_value = attrs.get("min_value", getattr(self.instance, "min_value", None))
        max_value = attrs.get("max_value", getattr(self.instance, "max_value", None))
        if min_value is not None and max_value is not None and min_value > max_value:
            raise serializers.ValidationError(
                {"max_value": "Maximum value cannot be less than minimum value."}
            )
        return attrs


class ProgramExpertSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)
    avatar = serializers.URLField(source="user.avatar", read_only=True)
    organization = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Expert
        fields = [
            "id",
            "user_id",
            "full_name",
            "organization",
            "email",
            "avatar",
            "status",
        ]

    def get_full_name(self, expert):
        user = expert.user
        return user.get_full_name() or user.email

    def get_organization(self, expert):
        return getattr(expert.user, "speciality", "") or getattr(
            expert.user, "status", ""
        )

    def get_status(self, expert):
        program = self.context.get("program")
        if program and expert.programs.filter(pk=program.pk).exists():
            return "added"
        return "available"


class EvaluationParticipantSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="id", read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ["user_id", "first_name", "last_name", "avatar", "full_name"]

    def get_full_name(self, user):
        return user.get_full_name() or user.email


class ProjectEvaluationCriterionSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = Criteria
        fields = [
            "id",
            "name",
            "description",
            "type",
            "min_value",
            "max_value",
            "weight",
            "value",
        ]

    def get_value(self, criterion):
        scores_by_criterion_id = self.context.get("scores_by_criterion_id", {})
        score = scores_by_criterion_id.get(criterion.id)
        return score.value if score else None


class ProjectEvaluationSerializer(serializers.ModelSerializer):
    scores = serializers.SerializerMethodField()

    class Meta:
        model = ProjectEvaluation
        fields = [
            "id",
            "status",
            "comment",
            "total_score",
            "submitted_at",
            "scores",
        ]

    def get_scores(self, evaluation):
        return [
            {"criterion_id": score.criterion_id, "value": score.value}
            for score in evaluation.evaluation_scores.all()
        ]


class ProjectSubmissionListSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(source="project.id", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    team_label = serializers.SerializerMethodField()
    team_name = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
    participants_count = serializers.SerializerMethodField()
    submitted_at = serializers.DateTimeField(source="datetime_submitted", read_only=True)
    evaluation = serializers.SerializerMethodField()
    evaluation_status = serializers.SerializerMethodField()

    class Meta:
        model = PartnerProgramProject
        fields = [
            "id",
            "project_id",
            "project_name",
            "team_label",
            "team_name",
            "participants",
            "participants_count",
            "submitted_at",
            "evaluation_status",
            "evaluation",
        ]

    def _get_evaluation(self, obj):
        if hasattr(obj, "_current_user_evaluations"):
            return obj._current_user_evaluations[0] if obj._current_user_evaluations else None
        request = self.context.get("request")
        if not request or not getattr(request.user, "is_authenticated", False):
            return None
        return obj.evaluations.filter(user=request.user).first()

    def _participants(self, obj):
        participants = []
        seen_user_ids = set()
        candidates = [obj.project.leader]
        collaborators = getattr(obj.project, "_prefetched_collaborators", None)
        if collaborators is None:
            collaborators = obj.project.collaborator_set.select_related("user").all()
        candidates.extend(collaborator.user for collaborator in collaborators)
        for user in candidates:
            if user.id in seen_user_ids:
                continue
            seen_user_ids.add(user.id)
            participants.append(user)
        return participants

    def get_team_label(self, obj):
        if obj.partner_program.participation_format == "individual":
            return "Individual project"
        return "Project team"

    def get_team_name(self, obj):
        if obj.partner_program.participation_format == "individual":
            user = obj.project.leader
            return user.get_full_name() or user.email
        return "Project team"

    def get_participants(self, obj):
        return EvaluationParticipantSerializer(self._participants(obj), many=True).data

    def get_participants_count(self, obj):
        return len(self._participants(obj))

    def get_evaluation(self, obj):
        evaluation = self._get_evaluation(obj)
        if not evaluation:
            return None
        return ProjectEvaluationSerializer(evaluation).data

    def get_evaluation_status(self, obj):
        evaluation = self._get_evaluation(obj)
        if not evaluation:
            return "not_started"
        return evaluation.status


class ProjectSubmissionDetailSerializer(ProjectSubmissionListSerializer):
    program = serializers.SerializerMethodField()
    project_description = serializers.CharField(
        source="project.description", read_only=True
    )
    materials = serializers.SerializerMethodField()
    criteria = serializers.SerializerMethodField()

    class Meta(ProjectSubmissionListSerializer.Meta):
        fields = ProjectSubmissionListSerializer.Meta.fields + [
            "program",
            "project_description",
            "materials",
            "criteria",
        ]

    def get_program(self, obj):
        program = obj.partner_program
        return {
            "id": program.id,
            "name": program.name,
            "participation_format": program.participation_format,
            "datetime_evaluation_ends": program.datetime_evaluation_ends,
        }

    def get_materials(self, obj):
        materials = []
        if obj.project.presentation_address:
            materials.append(
                {
                    "title": "presentation",
                    "url": obj.project.presentation_address,
                    "kind": "presentation",
                }
            )

        links = getattr(obj.project, "_prefetched_links", None)
        if links is None:
            links = obj.project.links.all()
        for index, link in enumerate(links, start=1):
            materials.append(
                {
                    "title": f"material-{index}",
                    "url": link.link,
                    "kind": "link",
                }
            )
        return materials

    def get_criteria(self, obj):
        evaluation = self._get_evaluation(obj)
        scores_by_criterion_id = {}
        if evaluation:
            scores_by_criterion_id = {
                score.criterion_id: score for score in evaluation.evaluation_scores.all()
            }
        criteria = Criteria.objects.filter(partner_program=obj.partner_program).order_by("id")
        return ProjectEvaluationCriterionSerializer(
            criteria,
            many=True,
            context={"scores_by_criterion_id": scores_by_criterion_id},
        ).data


class ProjectEvaluationScoreInputSerializer(serializers.Serializer):
    criterion_id = serializers.IntegerField()
    value = serializers.JSONField(allow_null=True, required=False)


class ProjectEvaluationSaveSerializer(serializers.Serializer):
    comment = serializers.CharField(allow_blank=True, required=False)
    scores = ProjectEvaluationScoreInputSerializer(many=True, required=False)


class ProjectScoreSerializer(serializers.ModelSerializer):
    criteria = CriteriaSerializer()
    expert_id = serializers.IntegerField(source="user_id", read_only=True)

    class Meta:
        model = ProjectScore
        fields = [
            "criteria",
            "expert_id",
            "value",
        ]

    def to_representation(self, instance):
        """For a 'flat' structure without nesting."""
        representation = super().to_representation(instance)
        criteria_data = representation.pop("criteria")
        return {**criteria_data, **representation}


class ProjectListForRateSerializer(serializers.ModelSerializer):
    views_count = serializers.SerializerMethodField()
    criterias = serializers.SerializerMethodField()
    scored = serializers.SerializerMethodField()
    rated_experts = serializers.SerializerMethodField()
    rated_count = serializers.SerializerMethodField()
    max_rates = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "leader",
            "description",
            "image_address",
            "presentation_address",
            "industry",
            "region",
            "views_count",
            "scored",
            "rated_experts",
            "rated_count",
            "max_rates",
            "criterias",
        ]

    def get_views_count(self, obj) -> int:
        return get_views_count(obj)

    def _get_program_scores(self, obj):
        if hasattr(obj, "_program_scores"):
            return obj._program_scores
        program_id = self.context["view"].kwargs.get("program_id")
        return ProjectScore.objects.filter(
            project=obj, criteria__partner_program_id=program_id
        ).select_related("criteria", "user")

    def _get_user_scores(self, obj):
        scores = self._get_program_scores(obj)
        request = self.context.get("request")
        if request and getattr(request.user, "is_authenticated", False):
            return [score for score in scores if score.user_id == request.user.id]
        return []

    def get_criterias(self, obj) -> CriteriasResponse | ProjectScoresResponse:
        user_scores = self._get_user_scores(obj)
        if user_scores:
            serializer = ProjectScoreSerializer(user_scores, many=True)
            return serializer.data
        program_id = self.context["view"].kwargs.get("program_id")
        criterias = Criteria.objects.filter(partner_program__id=program_id)
        serializer = CriteriaSerializer(criterias, many=True)
        return serializer.data

    def get_scored(self, obj) -> bool:
        user_scores = self._get_user_scores(obj)
        return bool(user_scores)

    def get_rated_experts(self, obj) -> list[int]:
        program_scores = self._get_program_scores(obj)
        return list({score.user_id for score in program_scores})

    def get_rated_count(self, obj) -> int:
        rated_attr = getattr(obj, "rated_count", None)
        if rated_attr is not None:
            return rated_attr
        program_scores = self._get_program_scores(obj)
        return len({score.user_id for score in program_scores})

    def get_max_rates(self, obj):
        return self.context.get("program_max_rates")
