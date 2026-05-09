from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from courses.models import Course, CourseAccessType, CourseContentStatus
from partner_programs.models import (
    PartnerProgram,
    PartnerProgramField,
    PartnerProgramProject,
    PartnerProgramUserProfile,
)
from partner_programs.serializers import PartnerProgramFieldValueUpdateSerializer
from partner_programs.services import publish_finished_program_projects
from partner_programs.views import (
    PartnerProgramDetail,
    PartnerProgramList,
    PartnerProgramProjectApplyView,
    PartnerProgramProjectSubmitView,
)
from projects.models import Company, Project


class PartnerProgramFieldValueUpdateSerializerInvalidTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.partner_program = PartnerProgram.objects.create(
            name="Тестовая программа",
            tag="test_tag",
            description="Описание тестовой программы",
            city="Москва",
            image_address="https://example.com/image.png",
            cover_image_address="https://example.com/cover.png",
            advertisement_image_address="https://example.com/advertisement.png",
            presentation_address="https://example.com/presentation.pdf",
            data_schema={},
            draft=True,
            projects_availability="all_users",
            datetime_registration_ends=now + timezone.timedelta(days=30),
            datetime_started=now,
            datetime_finished=now + timezone.timedelta(days=60),
        )

    def make_field(self, field_type, is_required, options=None):
        return PartnerProgramField.objects.create(
            partner_program=self.partner_program,
            name="test_field",
            label="Test Field",
            field_type=field_type,
            is_required=is_required,
            options="|".join(options) if options else "",
        )

    def test_required_text_field_empty(self):
        field = self.make_field("text", is_required=True)
        data = {"field_id": field.id, "value_text": ""}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "Поле должно содержать текстовое значение.", str(serializer.errors)
        )

    def test_required_textarea_field_null(self):
        field = self.make_field("textarea", is_required=True)
        data = {"field_id": field.id, "value_text": None}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "Поле должно содержать текстовое значение.", str(serializer.errors)
        )

    def test_checkbox_invalid_string(self):
        field = self.make_field("checkbox", is_required=True)
        data = {"field_id": field.id, "value_text": "maybe"}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("ожидается 'true' или 'false'", str(serializer.errors).lower())

    def test_checkbox_invalid_type(self):
        field = self.make_field("checkbox", is_required=True)
        data = {"field_id": field.id, "value_text": 1}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("ожидается 'true' или 'false'", str(serializer.errors).lower())

    def test_select_invalid_choice(self):
        field = self.make_field("select", is_required=True, options=["арбуз", "ананас"])
        data = {"field_id": field.id, "value_text": "яблоко"}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "Недопустимое значение для поля типа 'select'", str(serializer.errors)
        )

    def test_select_required_empty(self):
        field = self.make_field("select", is_required=True, options=["арбуз", "ананас"])
        data = {"field_id": field.id, "value_text": ""}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "Значение обязательно для поля типа 'select'", str(serializer.errors)
        )

    def test_radio_invalid_type(self):
        field = self.make_field("radio", is_required=True, options=["арбуз", "ананас"])
        data = {"field_id": field.id, "value_text": ["арбуз"]}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("Not a valid string.", str(serializer.errors))

    def test_radio_invalid_value(self):
        field = self.make_field("radio", is_required=True, options=["арбуз", "ананас"])
        data = {"field_id": field.id, "value_text": "груша"}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "Недопустимое значение для поля типа 'radio'", str(serializer.errors)
        )

    def test_file_invalid_type(self):
        field = self.make_field("file", is_required=True)
        data = {"field_id": field.id, "value_text": 123}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "Ожидается корректная ссылка (URL) на файл.", str(serializer.errors)
        )

    def test_file_empty_required(self):
        field = self.make_field("file", is_required=True)
        data = {"field_id": field.id, "value_text": ""}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("Файл обязателен для этого поля.", str(serializer.errors))


class PublishFinishedProgramProjectsTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="pass",
            first_name="User",
            last_name="Test",
            birthday="1990-01-01",
        )

    def create_program(self, **overrides):
        defaults = {
            "name": "Program",
            "tag": "program_tag",
            "description": "Program description",
            "city": "Moscow",
            "image_address": "https://example.com/image.png",
            "cover_image_address": "https://example.com/cover.png",
            "advertisement_image_address": "https://example.com/advertisement.png",
            "presentation_address": "https://example.com/presentation.pdf",
            "data_schema": {},
            "draft": False,
            "projects_availability": "all_users",
            "datetime_registration_ends": self.now - timezone.timedelta(days=5),
            "datetime_started": self.now - timezone.timedelta(days=30),
            "datetime_finished": self.now - timezone.timedelta(days=1),
        }
        defaults.update(overrides)
        return PartnerProgram.objects.create(**defaults)

    def create_project(self, **overrides):
        defaults = {
            "leader": self.user,
            "draft": False,
            "is_public": False,
            "name": "Project",
        }
        defaults.update(overrides)
        return Project.objects.create(**defaults)

    def test_publish_updates_projects_from_both_sources(self):
        program = self.create_program(publish_projects_after_finish=True)

        link_project = self.create_project(name="Linked Project")
        PartnerProgramProject.objects.create(
            partner_program=program,
            project=link_project,
        )

        profile_project = self.create_project(name="Profile Project")
        PartnerProgramUserProfile.objects.create(
            user=self.user,
            partner_program=program,
            project=profile_project,
            partner_program_data={},
        )

        publish_finished_program_projects()

        link_project.refresh_from_db()
        profile_project.refresh_from_db()
        self.assertTrue(link_project.is_public)
        self.assertTrue(profile_project.is_public)

    def test_publish_skips_draft_projects(self):
        program = self.create_program(publish_projects_after_finish=True)
        draft_project = self.create_project(draft=True, name="Draft Project")
        PartnerProgramProject.objects.create(
            partner_program=program,
            project=draft_project,
        )

        publish_finished_program_projects()

        draft_project.refresh_from_db()
        self.assertFalse(draft_project.is_public)

    def test_publish_skips_when_flag_false(self):
        program = self.create_program(publish_projects_after_finish=False)
        project = self.create_project(name="Private Project")
        PartnerProgramProject.objects.create(
            partner_program=program,
            project=project,
        )

        publish_finished_program_projects()

        project.refresh_from_db()
        self.assertFalse(project.is_public)

    def test_publish_after_flag_enabled_post_finish(self):
        program = self.create_program(publish_projects_after_finish=False)
        project = self.create_project(name="Delayed Project")
        PartnerProgramProject.objects.create(
            partner_program=program,
            project=project,
        )

        publish_finished_program_projects()
        project.refresh_from_db()
        self.assertFalse(project.is_public)

        program.publish_projects_after_finish = True
        program.save(update_fields=["publish_projects_after_finish"])

        publish_finished_program_projects()
        project.refresh_from_db()
        self.assertTrue(project.is_public)


class PartnerProgramCoreListTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = PartnerProgramList.as_view()
        self.now = timezone.now()

    def create_program(self, **overrides):
        defaults = {
            "name": "Core Program",
            "tag": "core_program",
            "description": "Program description",
            "city": "Moscow",
            "data_schema": {},
            "draft": False,
            "status": PartnerProgram.STATUS_PUBLISHED,
            "projects_availability": "all_users",
            "datetime_registration_ends": self.now + timezone.timedelta(days=10),
            "datetime_started": self.now - timezone.timedelta(days=1),
            "datetime_finished": self.now + timezone.timedelta(days=30),
        }
        defaults.update(overrides)
        return PartnerProgram.objects.create(**defaults)

    def test_list_returns_only_catalog_visible_programs(self):
        published_program = self.create_program(name="Published program")
        self.create_program(
            name="Draft program",
            draft=True,
            status=PartnerProgram.STATUS_DRAFT,
        )

        request = self.factory.get("/programs/")
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], published_program.id)

    def test_list_includes_company_summary(self):
        company = Company.objects.create(name="Organizer", inn="1234567890")
        program = self.create_program(company=company)

        request = self.factory.get("/programs/")
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        program_data = response.data["results"][0]
        self.assertEqual(program_data["id"], program.id)
        self.assertEqual(program_data["company_name"], "Organizer")
        self.assertEqual(
            program_data["company"],
            {"id": company.id, "name": "Organizer", "inn": "1234567890"},
        )


class PartnerProgramProjectApplyViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = PartnerProgramProjectApplyView.as_view()
        self.now = timezone.now()
        self.user = get_user_model().objects.create_user(
            email="leader@example.com",
            password="pass",
            first_name="Leader",
            last_name="User",
            birthday="1990-01-01",
        )

    def create_program(self, **overrides):
        defaults = {
            "name": "Program",
            "tag": f"program_{PartnerProgram.objects.count()}",
            "description": "Program description",
            "city": "Moscow",
            "data_schema": {},
            "draft": False,
            "projects_availability": "all_users",
            "datetime_registration_ends": self.now + timezone.timedelta(days=10),
            "datetime_started": self.now - timezone.timedelta(days=1),
            "datetime_finished": self.now + timezone.timedelta(days=30),
            "is_competitive": True,
        }
        defaults.update(overrides)
        return PartnerProgram.objects.create(**defaults)

    def create_profile(self, program, user=None):
        return PartnerProgramUserProfile.objects.create(
            user=user or self.user,
            partner_program=program,
            partner_program_data={},
        )

    def create_project(self, **overrides):
        defaults = {
            "leader": self.user,
            "draft": True,
            "is_public": False,
            "name": "Reusable Project",
        }
        defaults.update(overrides)
        return Project.objects.create(**defaults)

    def post_apply(self, program, data, user=None):
        request = self.factory.post(
            f"/partner-programs/{program.pk}/projects/apply/",
            data,
            format="json",
        )
        force_authenticate(request, user=user or self.user)
        return self.view(request, pk=program.pk)

    def test_apply_links_existing_leader_project(self):
        program = self.create_program()
        profile = self.create_profile(program)
        project = self.create_project()

        response = self.post_apply(program, {"project_id": project.id})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["project_id"], project.id)
        program_link = PartnerProgramProject.objects.get(
            partner_program=program,
            project=project,
        )
        self.assertEqual(response.data["program_link_id"], program_link.id)
        profile.refresh_from_db()
        self.assertEqual(profile.project_id, project.id)

    def test_apply_rejects_existing_project_from_another_leader(self):
        program = self.create_program()
        self.create_profile(program)
        other_user = get_user_model().objects.create_user(
            email="other@example.com",
            password="pass",
            first_name="Other",
            last_name="Leader",
            birthday="1990-01-01",
        )
        project = self.create_project(leader=other_user)

        response = self.post_apply(program, {"project_id": project.id})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            PartnerProgramProject.objects.filter(
                partner_program=program,
                project=project,
            ).exists()
        )

    def test_apply_rejects_project_already_linked_to_another_program(self):
        program = self.create_program()
        other_program = self.create_program()
        self.create_profile(program)
        project = self.create_project()
        PartnerProgramProject.objects.create(
            partner_program=other_program,
            project=project,
        )

        response = self.post_apply(program, {"project_id": project.id})

        self.assertEqual(response.status_code, 400)
        self.assertIn("project_id", response.data)
        self.assertFalse(
            PartnerProgramProject.objects.filter(
                partner_program=program,
                project=project,
            ).exists()
        )


class PartnerProgramProjectSubmitViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = PartnerProgramProjectSubmitView.as_view()
        self.now = timezone.now()
        self.user = get_user_model().objects.create_user(
            email="leader@example.com",
            password="pass",
            first_name="Leader",
            last_name="User",
            birthday="1990-01-01",
        )

    def create_program(self, **overrides):
        defaults = {
            "name": "Program",
            "tag": "program_tag",
            "description": "Program description",
            "city": "Moscow",
            "data_schema": {},
            "draft": False,
            "projects_availability": "all_users",
            "datetime_registration_ends": self.now + timezone.timedelta(days=10),
            "datetime_started": self.now - timezone.timedelta(days=1),
            "datetime_finished": self.now + timezone.timedelta(days=30),
            "is_competitive": True,
        }
        defaults.update(overrides)
        return PartnerProgram.objects.create(**defaults)

    def create_project_link(self, program):
        project = Project.objects.create(
            leader=self.user,
            draft=False,
            is_public=False,
            name="Project",
        )
        return PartnerProgramProject.objects.create(
            partner_program=program,
            project=project,
        )

    def test_submit_blocked_after_deadline(self):
        program = self.create_program(
            datetime_project_submission_ends=self.now - timezone.timedelta(days=1)
        )
        link = self.create_project_link(program)

        request = self.factory.post(
            f"partner-program-projects/{link.pk}/submit/"
        )
        force_authenticate(request, user=self.user)
        response = self.view(request, pk=link.pk)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data.get("detail"),
            "Срок подачи проектов в программу завершён.",
        )
        link.refresh_from_db()
        self.assertFalse(link.submitted)

    def test_submit_allowed_before_deadline(self):
        program = self.create_program(
            datetime_project_submission_ends=self.now + timezone.timedelta(days=1)
        )
        link = self.create_project_link(program)

        request = self.factory.post(
            f"partner-program-projects/{link.pk}/submit/"
        )
        force_authenticate(request, user=self.user)
        response = self.view(request, pk=link.pk)

        self.assertEqual(response.status_code, 200)
        link.refresh_from_db()
        self.assertTrue(link.submitted)
        self.assertIsNotNone(link.datetime_submitted)

    def test_submit_rejects_project_that_violates_team_rules(self):
        program = self.create_program(
            datetime_project_submission_ends=self.now + timezone.timedelta(days=1),
            participation_format=PartnerProgram.PARTICIPATION_FORMAT_TEAM,
            project_team_min_size=2,
        )
        link = self.create_project_link(program)

        request = self.factory.post(
            f"partner-program-projects/{link.pk}/submit/"
        )
        force_authenticate(request, user=self.user)
        response = self.view(request, pk=link.pk)

        self.assertEqual(response.status_code, 400)
        link.refresh_from_db()
        self.assertFalse(link.submitted)


class PartnerProgramFieldValueUpdateSerializerValidTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.partner_program = PartnerProgram.objects.create(
            name="Тестовая программа",
            tag="test_tag",
            description="Описание тестовой программы",
            city="Москва",
            image_address="https://example.com/image.png",
            cover_image_address="https://example.com/cover.png",
            advertisement_image_address="https://example.com/advertisement.png",
            presentation_address="https://example.com/presentation.pdf",
            data_schema={},
            draft=True,
            projects_availability="all_users",
            datetime_registration_ends=now + timezone.timedelta(days=30),
            datetime_started=now,
            datetime_finished=now + timezone.timedelta(days=60),
        )

    def make_field(self, field_type, is_required, options=None):
        return PartnerProgramField.objects.create(
            partner_program=self.partner_program,
            name="test_field",
            label="Test Field",
            field_type=field_type,
            is_required=is_required,
            options="|".join(options) if options else "",
        )

    def test_optional_text_field_valid(self):
        field = self.make_field("text", is_required=False)
        data = {"field_id": field.id, "value_text": "some value"}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_required_text_field_valid(self):
        field = self.make_field("text", is_required=True)
        data = {"field_id": field.id, "value_text": "not empty"}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_optional_textarea_valid(self):
        field = self.make_field("textarea", is_required=False)
        data = {"field_id": field.id, "value_text": "optional long text"}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_required_textarea_valid(self):
        field = self.make_field("textarea", is_required=True)
        data = {"field_id": field.id, "value_text": "required long text"}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_checkbox_true_valid(self):
        field = self.make_field("checkbox", is_required=True)
        data = {"field_id": field.id, "value_text": "true"}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_checkbox_false_valid(self):
        field = self.make_field("checkbox", is_required=False)
        data = {"field_id": field.id, "value_text": "false"}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_select_valid(self):
        field = self.make_field("select", is_required=True, options=["арбуз", "ананас"])
        data = {"field_id": field.id, "value_text": "ананас"}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_radio_valid(self):
        field = self.make_field(
            "radio", is_required=True, options=["арбуз", "апельсин"]
        )
        data = {"field_id": field.id, "value_text": "апельсин"}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_optional_select_empty_valid(self):
        field = self.make_field(
            "select", is_required=False, options=["арбуз", "апельсин"]
        )
        data = {"field_id": field.id, "value_text": ""}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_file_valid_url(self):
        field = self.make_field("file", is_required=True)
        data = {"field_id": field.id, "value_text": "https://example.com/file.pdf"}
        serializer = PartnerProgramFieldValueUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())


class PartnerProgramDetailCoursesTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = PartnerProgramDetail.as_view()
        self.now = timezone.now()

    def create_program(self, **overrides):
        defaults = {
            "name": "Program with courses",
            "tag": "program_with_courses",
            "description": "Program description",
            "city": "Moscow",
            "data_schema": {},
            "draft": False,
            "projects_availability": "all_users",
            "datetime_registration_ends": self.now + timezone.timedelta(days=10),
            "datetime_started": self.now - timezone.timedelta(days=1),
            "datetime_finished": self.now + timezone.timedelta(days=30),
        }
        defaults.update(overrides)
        return PartnerProgram.objects.create(**defaults)

    def create_user(self, email: str):
        return get_user_model().objects.create_user(
            email=email,
            password="pass",
            first_name="Test",
            last_name="User",
            birthday="1990-01-01",
        )

    def create_course(self, program: PartnerProgram, **overrides):
        defaults = {
            "title": "Program course",
            "partner_program": program,
            "access_type": CourseAccessType.ALL_USERS,
            "status": CourseContentStatus.PUBLISHED,
        }
        defaults.update(overrides)
        return Course.objects.create(**defaults)

    def test_detail_includes_related_courses_with_availability_for_member(self):
        program = self.create_program()
        member = self.create_user("member-program@example.com")
        PartnerProgramUserProfile.objects.create(
            user=member,
            partner_program=program,
            project=None,
            partner_program_data={},
        )
        all_users_course = self.create_course(
            program,
            title="Open course",
            access_type=CourseAccessType.ALL_USERS,
        )
        member_course = self.create_course(
            program,
            title="Members course",
            access_type=CourseAccessType.PROGRAM_MEMBERS,
        )
        self.create_course(
            program,
            title="Draft course",
            access_type=CourseAccessType.ALL_USERS,
            status=CourseContentStatus.DRAFT,
        )

        request = self.factory.get(f"/programs/{program.id}/")
        force_authenticate(request, user=member)
        response = self.view(request, pk=program.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["courses"],
            [
                {
                    "id": all_users_course.id,
                    "title": "Open course",
                    "is_available": True,
                },
                {
                    "id": member_course.id,
                    "title": "Members course",
                    "is_available": True,
                },
            ],
        )

    def test_detail_includes_empty_courses_list_when_program_has_no_related_courses(self):
        program = self.create_program()
        user = self.create_user("plain-user@example.com")

        request = self.factory.get(f"/programs/{program.id}/")
        force_authenticate(request, user=user)
        response = self.view(request, pk=program.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["courses"], [])

    def test_detail_marks_program_only_courses_as_unavailable_for_non_member(self):
        program = self.create_program()
        outsider = self.create_user("outsider-program@example.com")
        open_course = self.create_course(
            program,
            title="Open course",
            access_type=CourseAccessType.ALL_USERS,
        )
        member_course = self.create_course(
            program,
            title="Members course",
            access_type=CourseAccessType.PROGRAM_MEMBERS,
        )

        request = self.factory.get(f"/programs/{program.id}/")
        force_authenticate(request, user=outsider)
        response = self.view(request, pk=program.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["courses"],
            [
                {
                    "id": open_course.id,
                    "title": "Open course",
                    "is_available": True,
                },
                {
                    "id": member_course.id,
                    "title": "Members course",
                    "is_available": False,
                },
            ],
        )


class PartnerProgramDetailParticipantProjectTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = PartnerProgramDetail.as_view()
        self.now = timezone.now()

    def create_user(self, email: str):
        return get_user_model().objects.create_user(
            email=email,
            password="pass",
            first_name="Test",
            last_name="User",
            birthday="1990-01-01",
        )

    def create_program(self, **overrides):
        defaults = {
            "name": "Program with participant project",
            "tag": f"participant_project_{PartnerProgram.objects.count()}",
            "description": "Program description",
            "city": "Moscow",
            "data_schema": {},
            "draft": False,
            "projects_availability": "all_users",
            "datetime_registration_ends": self.now + timezone.timedelta(days=10),
            "datetime_started": self.now - timezone.timedelta(days=1),
            "datetime_finished": self.now + timezone.timedelta(days=30),
        }
        defaults.update(overrides)
        return PartnerProgram.objects.create(**defaults)

    def create_project(self, user, **overrides):
        defaults = {
            "leader": user,
            "draft": True,
            "is_public": False,
            "name": "Participant project",
            "description": "Project description",
            "presentation_address": "https://example.com/presentation.pdf",
        }
        defaults.update(overrides)
        return Project.objects.create(**defaults)

    def test_detail_includes_current_member_project_state(self):
        user = self.create_user("member-project@example.com")
        program = self.create_program()
        project = self.create_project(user)
        link = PartnerProgramProject.objects.create(
            partner_program=program,
            project=project,
        )
        PartnerProgramUserProfile.objects.create(
            user=user,
            partner_program=program,
            project=project,
            partner_program_data={},
        )

        request = self.factory.get(f"/programs/{program.id}/")
        force_authenticate(request, user=user)
        response = self.view(request, pk=program.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["program_link_id"], link.id)
        self.assertEqual(response.data["participant_project_status"], "not_submitted")
        self.assertIsNone(response.data["participant_project_submitted_at"])
        self.assertEqual(response.data["participant_project"]["id"], project.id)
        self.assertEqual(
            response.data["participant_project"]["partner_program"]["program_link_id"],
            link.id,
        )
        self.assertFalse(
            response.data["participant_project"]["partner_program"]["submitted"]
        )

    def test_detail_includes_submitted_project_state(self):
        user = self.create_user("submitted-project@example.com")
        program = self.create_program()
        project = self.create_project(user)
        submitted_at = timezone.now()
        link = PartnerProgramProject.objects.create(
            partner_program=program,
            project=project,
            submitted=True,
            datetime_submitted=submitted_at,
        )
        PartnerProgramUserProfile.objects.create(
            user=user,
            partner_program=program,
            project=project,
            partner_program_data={},
        )

        request = self.factory.get(f"/programs/{program.id}/")
        force_authenticate(request, user=user)
        response = self.view(request, pk=program.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["program_link_id"], link.id)
        self.assertEqual(response.data["participant_project_status"], "submitted")
        self.assertEqual(
            response.data["participant_project_submitted_at"],
            submitted_at.isoformat(),
        )
        self.assertTrue(
            response.data["participant_project"]["partner_program"]["submitted"]
        )
