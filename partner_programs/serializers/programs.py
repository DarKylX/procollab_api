from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.services import get_likes_count, get_links, get_views_count, is_fan
from courses.models import CourseContentStatus
from courses.services.access import resolve_course_availability
from moderation.models import ModerationLog
from partner_programs.models import (
    LegalDocument,
    PartnerProgram,
    PartnerProgramField,
    PartnerProgramFieldValue,
    PartnerProgramMaterial,
    PartnerProgramProject,
    PartnerProgramUserProfile,
)
from projects.models import Project
from projects.validators import validate_project

from .fields import PartnerProgramFieldValueUpdateSerializer

User = get_user_model()


class LegalDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalDocument
        fields = (
            "id",
            "type",
            "title",
            "version",
            "content_url",
            "content_html",
        )


def _company_summary(company):
    if not company:
        return None
    return {
        "id": company.id,
        "name": company.name,
        "inn": company.inn,
    }


def _verified_company_name(program: PartnerProgram) -> str:
    if program.verification_status != PartnerProgram.VERIFICATION_STATUS_VERIFIED:
        return ""

    from partner_programs.verification_services import (
        latest_approved_verification_request,
    )

    request = latest_approved_verification_request(program)
    if request and request.company_name:
        return request.company_name
    return program.company.name if program.company_id and program.company else ""


def _is_verified(program: PartnerProgram) -> bool:
    return program.verification_status == PartnerProgram.VERIFICATION_STATUS_VERIFIED


def _latest_program_log(program: PartnerProgram, actions):
    prefetched_logs = getattr(program, "_prefetched_objects_cache", {}).get(
        "moderation_logs"
    )
    if prefetched_logs is not None:
        logs = [log for log in prefetched_logs if log.action in actions]
        if not logs:
            return None
        return max(logs, key=lambda log: (log.datetime_created, log.id))

    return (
        program.moderation_logs.select_related("author")
        .filter(action__in=actions)
        .order_by("-datetime_created", "-id")
        .first()
    )


def _can_view_moderation_result(user, program: PartnerProgram) -> bool:
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and (
            getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
            or program.is_manager(user)
        )
    )


def _rejection_reason_label(reason_code: str) -> str:
    return dict(ModerationLog.REJECTION_REASON_CHOICES).get(reason_code, "")


class PartnerProgramListSerializer(serializers.ModelSerializer):
    """Serializer for PartnerProgram model for list view."""

    company = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    verified_company_name = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField(method_name="count_likes")
    views_count = serializers.SerializerMethodField(method_name="count_views")
    short_description = serializers.SerializerMethodField(
        method_name="get_short_description"
    )
    is_user_liked = serializers.SerializerMethodField(method_name="get_is_user_liked")
    is_user_member = serializers.SerializerMethodField(method_name="get_is_user_member")

    def _get_user(self):
        user = self.context.get("user")
        if user:
            return user
        request = self.context.get("request")
        if request:
            return request.user
        return None

    def count_likes(self, program):
        return get_likes_count(program)

    def count_views(self, program):
        return get_views_count(program)

    def get_short_description(self, program):
        if not program.description:
            return ""
        return program.description[:125]

    def get_is_user_liked(self, obj):
        # fixme: copy-paste in every serializer...
        user = self._get_user()
        if user and user.is_authenticated:
            return is_fan(obj, user)
        return False

    def get_is_user_member(self, program):
        if hasattr(program, "is_user_member"):
            return bool(program.is_user_member)
        user = self._get_user()
        if not user or not user.is_authenticated:
            return False
        return program.users.filter(pk=user.pk).exists()

    def get_company(self, program):
        return _company_summary(program.company)

    def get_company_name(self, program):
        return program.company.name if program.company_id and program.company else ""

    def get_is_verified(self, program: PartnerProgram) -> bool:
        return _is_verified(program)

    def get_verified_company_name(self, program: PartnerProgram) -> str:
        return _verified_company_name(program)

    class Meta:
        model = PartnerProgram
        fields = (
            "id",
            "status",
            "frozen_at",
            "verification_status",
            "is_verified",
            "name",
            "city",
            "image_address",
            "short_description",
            "company",
            "company_name",
            "verified_company_name",
            "is_private",
            "registration_link",
            "datetime_registration_ends",
            "datetime_project_submission_ends",
            "datetime_evaluation_ends",
            "publish_projects_after_finish",
            "participation_format",
            "project_team_min_size",
            "project_team_max_size",
            "readiness",
            "datetime_started",
            "datetime_finished",
            "views_count",
            "likes_count",
            "is_user_liked",
            "is_user_member",
        )


class PartnerProgramBaseSerializerMixin(serializers.ModelSerializer):
    """
    Базовый миксин для сериализаторов PartnerProgram,
    включает общие поля: materials и is_user_manager.
    """

    materials = serializers.SerializerMethodField()
    is_user_manager = serializers.SerializerMethodField()
    courses = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    verified_company_name = serializers.SerializerMethodField()
    is_frozen = serializers.SerializerMethodField()
    frozen_message = serializers.SerializerMethodField()
    freeze_reason = serializers.SerializerMethodField()
    moderation_result = serializers.SerializerMethodField()

    def get_materials(self, program: PartnerProgram):
        materials = program.materials.all()
        return PartnerProgramMaterialSerializer(materials, many=True).data

    def get_is_user_manager(self, program: PartnerProgram) -> bool:
        user = self.context.get("user")
        return bool(user and program.is_manager(user))

    def get_courses(self, program: PartnerProgram) -> list[dict]:
        user = self.context.get("user")
        prefetched_courses = (
            getattr(program, "_prefetched_objects_cache", {}).get("courses")
            if hasattr(program, "_prefetched_objects_cache")
            else None
        )
        if prefetched_courses is None:
            related_courses = program.courses.exclude(
                status=CourseContentStatus.DRAFT
            ).order_by("id")
        else:
            related_courses = sorted(
                (
                    course
                    for course in prefetched_courses
                    if course.status != CourseContentStatus.DRAFT
                ),
                key=lambda course: course.id,
            )

        return [
            {
                "id": course.id,
                "title": course.title,
                "is_available": resolve_course_availability(course, user).is_available,
            }
            for course in related_courses
        ]

    def get_company(self, program: PartnerProgram):
        return _company_summary(program.company)

    def get_company_name(self, program: PartnerProgram) -> str:
        return program.company.name if program.company_id and program.company else ""

    def get_is_verified(self, program: PartnerProgram) -> bool:
        return _is_verified(program)

    def get_verified_company_name(self, program: PartnerProgram) -> str:
        return _verified_company_name(program)

    def get_is_frozen(self, program: PartnerProgram) -> bool:
        return program.status == PartnerProgram.STATUS_FROZEN

    def get_frozen_message(self, program: PartnerProgram) -> str:
        if program.status != PartnerProgram.STATUS_FROZEN:
            return ""
        return "Program is temporarily frozen."

    def get_freeze_reason(self, program: PartnerProgram) -> str:
        log = _latest_program_log(
            program,
            (ModerationLog.ACTION_FREEZE, ModerationLog.ACTION_AUTO_FREEZE),
        )
        return log.comment if log else ""

    def get_moderation_result(self, program: PartnerProgram):
        if program.status != PartnerProgram.STATUS_REJECTED:
            return None

        user = self.context.get("user")
        if not user:
            request = self.context.get("request")
            user = getattr(request, "user", None) if request else None

        if not _can_view_moderation_result(user, program):
            return None

        log = _latest_program_log(program, ModerationLog.REJECT_ACTIONS)
        if not log:
            return None

        rejected_by = None
        if log.author:
            rejected_by = {
                "id": log.author_id,
                "email": log.author.email,
                "full_name": log.author.get_full_name() or log.author.email,
            }

        return {
            "action": log.action,
            "comment": log.comment,
            "reason_code": log.rejection_reason,
            "reason_label": _rejection_reason_label(log.rejection_reason),
            "rejection_reason_code": log.rejection_reason,
            "rejection_comment": log.comment,
            "created_at": log.datetime_created,
            "rejected_at": log.datetime_created,
            "sections_to_fix": log.sections_to_fix,
            "rejected_by": rejected_by,
        }

    class Meta:
        abstract = True


class PartnerProgramForMemberSerializer(PartnerProgramBaseSerializerMixin):
    """Serializer for PartnerProgram model for member of this program"""

    views_count = serializers.SerializerMethodField(method_name="count_views")
    links = serializers.SerializerMethodField(method_name="get_links")
    is_user_manager = serializers.SerializerMethodField(method_name="get_is_user_manager")
    program_link_id = serializers.SerializerMethodField()
    participant_project = serializers.SerializerMethodField()
    participant_project_status = serializers.SerializerMethodField()
    participant_project_submitted_at = serializers.SerializerMethodField()

    def _get_participant_program_link(self, program: PartnerProgram):
        cache = getattr(self, "_participant_program_link_cache", None)
        if cache is None:
            cache = {}
            self._participant_program_link_cache = cache

        if program.pk in cache:
            return cache[program.pk]

        user = self.context.get("user")
        if not user or not user.is_authenticated:
            cache[program.pk] = None
            return None

        link = (
            PartnerProgramProject.objects.select_related("project")
            .filter(partner_program=program, project__leader=user)
            .first()
        )
        if not link:
            profile = (
                PartnerProgramUserProfile.objects.select_related("project")
                .filter(partner_program=program, user=user)
                .first()
            )
            if profile and profile.project_id:
                link = (
                    PartnerProgramProject.objects.select_related("project")
                    .filter(partner_program=program, project=profile.project)
                    .first()
                )

        cache[program.pk] = link
        return link

    def count_views(self, program):
        return get_views_count(program)

    def get_links(self, program):
        # TODO: add caching here at least every 5 minutes, otherwise this will be heavy load
        # fixme: create LinksSerializer mb?
        return [link.link for link in get_links(program)]

    def get_is_user_liked(self, obj):
        # fixme: copy-paste in every serializer...
        user = self.context.get("user")
        if user:
            return is_fan(obj, user)
        return False

    def get_program_link_id(self, program: PartnerProgram):
        link = self._get_participant_program_link(program)
        return link.id if link else None

    def get_participant_project(self, program: PartnerProgram):
        link = self._get_participant_program_link(program)
        if not link or not link.project:
            return None

        project = link.project
        return {
            "id": project.id,
            "name": project.name or "",
            "description": project.description or "",
            "short_description": project.get_short_description() or "",
            "image_address": project.image_address or "",
            "cover_image_address": project.cover_image_address or "",
            "presentation_address": project.presentation_address or "",
            "draft": project.draft,
            "partner_program": {
                "program_link_id": link.id,
                "program_id": link.partner_program_id,
                "is_submitted": link.submitted,
                "submitted": link.submitted,
                "submitted_at": link.datetime_submitted.isoformat()
                if link.datetime_submitted
                else None,
            },
        }

    def get_participant_project_status(self, program: PartnerProgram) -> str:
        link = self._get_participant_program_link(program)
        if not link:
            return "not_linked"
        return "submitted" if link.submitted else "not_submitted"

    def get_participant_project_submitted_at(self, program: PartnerProgram):
        link = self._get_participant_program_link(program)
        if not link or not link.datetime_submitted:
            return None
        return link.datetime_submitted.isoformat()

    class Meta:
        model = PartnerProgram
        fields = (
            "id",
            "status",
            "frozen_at",
            "verification_status",
            "is_verified",
            "name",
            "tag",
            "description",
            "city",
            "company",
            "company_name",
            "verified_company_name",
            "links",
            "materials",
            "image_address",
            "cover_image_address",
            "presentation_address",
            "registration_link",
            "is_private",
            "views_count",
            "datetime_registration_ends",
            "datetime_project_submission_ends",
            "datetime_evaluation_ends",
            "publish_projects_after_finish",
            "participation_format",
            "project_team_min_size",
            "project_team_max_size",
            "program_link_id",
            "participant_project",
            "participant_project_status",
            "participant_project_submitted_at",
            "freeze_reason",
            "moderation_result",
            "readiness",
            "is_user_manager",
            "courses",
        )


class PartnerProgramForUnregisteredUserSerializer(PartnerProgramBaseSerializerMixin):
    """Serializer for PartnerProgram model for unregistered users in the program"""

    class Meta:
        model = PartnerProgram
        fields = (
            "id",
            "status",
            "frozen_at",
            "is_frozen",
            "frozen_message",
            "verification_status",
            "is_verified",
            "name",
            "tag",
            "city",
            "company",
            "company_name",
            "verified_company_name",
            "materials",
            "image_address",
            "cover_image_address",
            "advertisement_image_address",
            "presentation_address",
            "registration_link",
            "is_private",
            "datetime_registration_ends",
            "datetime_project_submission_ends",
            "datetime_evaluation_ends",
            "publish_projects_after_finish",
            "participation_format",
            "project_team_min_size",
            "project_team_max_size",
            "freeze_reason",
            "moderation_result",
            "readiness",
            "is_user_manager",
            "courses",
        )


class PartnerProgramNewUserSerializer(serializers.ModelSerializer):
    """Serializer for creating new user and register him to program."""

    program_data = serializers.JSONField(required=True)

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "first_name",
            "last_name",
            "patronymic",
            "program_data",
        )


class PartnerProgramUserSerializer(serializers.Serializer):
    program_data = serializers.JSONField(required=True)


class PartnerProgramDataSchemaSerializer(serializers.Serializer):
    data_schema = serializers.JSONField(required=True)


class UserProgramsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerProgram
        fields = [
            "id",
            "name",
            "tag",
        ]


class PartnerProgramMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerProgramMaterial
        fields = ("title", "url")


class PartnerProgramFieldValueSerializer(serializers.ModelSerializer):
    field_name = serializers.CharField(source="field.name")
    value = serializers.SerializerMethodField()

    class Meta:
        model = PartnerProgramFieldValue
        fields = [
            "field_name",
            "value",
        ]

    def get_value(self, obj):
        if obj.field.field_type == "file":
            return obj.value_file.link if obj.value_file else None
        return obj.value_text


class PartnerProgramFieldSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()

    class Meta:
        model = PartnerProgramField
        fields = [
            "id",
            "name",
            "label",
            "field_type",
            "is_required",
            "show_filter",
            "help_text",
            "options",
        ]

    def get_options(self, obj):
        return obj.get_options_list()


class ProgramProjectFilterRequestSerializer(serializers.Serializer):
    filters = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        required=False,
        help_text="Словарь: ключ = PartnerProgramField.name, значение = список выбранных опций",
    )
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(
        required=False, default=20, min_value=1, max_value=200
    )
    MAX_FILTERS = 3

    def validate_filters(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Поле filters должно быть объектом (словарём ключ-значение)"
            )

        if len(value) > self.MAX_FILTERS:
            raise serializers.ValidationError(
                f"Можно передать не более {self.MAX_FILTERS} фильтров."
            )

        cleaned: dict = {}
        for key, raw_values in value.items():
            if not isinstance(key, str) or not key.strip():
                raise serializers.ValidationError(
                    f"Ключи фильтров должны быть непустыми строками. Некорректный ключ: {key}"
                )

            if isinstance(raw_values, list):
                normalized_values = [
                    str(item).strip() for item in raw_values if str(item).strip() != ""
                ]
            else:
                normalized_values = (
                    [str(raw_values).strip()] if str(raw_values).strip() != "" else []
                )

            if not normalized_values:
                continue

            cleaned[key.strip()] = normalized_values

        return cleaned


class ProgramProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "name",
            "description",
            "region",
            "industry",
            "presentation_address",
            "image_address",
            "cover_image_address",
            "actuality",
            "problem",
            "target_audience",
            "implementation_deadline",
            "trl",
            "is_company",
        ]

    def validate(self, data):
        validate_project({**data, "draft": True})
        return data


class PartnerProgramProjectApplySerializer(serializers.Serializer):
    project = ProgramProjectCreateSerializer(required=False)
    project_id = serializers.IntegerField(required=False)
    program_field_values = PartnerProgramFieldValueUpdateSerializer(
        many=True, required=False
    )

    def validate(self, data):
        has_project = "project" in data
        has_project_id = data.get("project_id") is not None
        if has_project == has_project_id:
            raise serializers.ValidationError("Provide either project or project_id.")
        return data
