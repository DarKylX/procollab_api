import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from certificates.enums import (
    FIELD_TEAM_MEMBERS,
    ISSUE_CONDITION_ALL_REGISTERED,
    ISSUE_CONDITION_SCORE_THRESHOLD,
    ISSUE_CONDITION_SUBMITTED_PROJECT,
    ISSUE_CONDITION_TOP_POSITIONS,
    RELEASE_MODE_AFTER_PROGRAM_END,
    RELEASE_MODE_MANUAL,
)
from certificates.models import (
    CertificateGenerationRun,
    IssuedCertificate,
    ProgramCertificateTemplate,
)
from certificates.services import (
    CertificateRecipient,
    generate_certificate_for_user,
    generate_certificates_for_program_sync,
    get_certificate_recipients,
    render_certificate_html,
)
from certificates.tasks import complete_finished_programs, generate_certificates_for_program
from certificates.views import (
    IssuedCertificateDeleteView,
    MyProgramCertificateView,
    ProgramCertificateDownloadView,
    ProgramCertificateGenerationStatsView,
    ProgramCertificateListView,
    ProgramCertificateReleaseView,
)
from files.models import UserFile
from partner_programs.models import (
    PartnerProgram,
    PartnerProgramProject,
    PartnerProgramUserProfile,
)
from projects.models import Collaborator, Project

TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="certificates-generation-tests-"))


@override_settings(
    DEBUG=True,
    MEDIA_ROOT=TEST_MEDIA_ROOT,
    LOCAL_MEDIA_BASE_URL="http://127.0.0.1:8000",
    FRONTEND_URL="https://app.test",
    DEFAULT_FROM_EMAIL="from@test",
)
class CertificateGenerationTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.factory = APIRequestFactory()
        self.my_certificate_view = MyProgramCertificateView.as_view()
        self.stats_view = ProgramCertificateGenerationStatsView.as_view()
        self.delete_view = IssuedCertificateDeleteView.as_view()
        self.download_view = ProgramCertificateDownloadView.as_view()
        self.list_view = ProgramCertificateListView.as_view()
        self.release_view = ProgramCertificateReleaseView.as_view()
        self.now = timezone.now()
        self.file_index = 0

        self.admin = self.create_user("certificate-admin@example.com", is_staff=True)
        self.manager = self.create_user("certificate-manager-07@example.com")
        self.user_1 = self.create_user("certificate-user-1@example.com")
        self.user_2 = self.create_user("certificate-user-2@example.com")
        self.user_3 = self.create_user("certificate-user-3@example.com")
        self.outsider = self.create_user("certificate-outsider-07@example.com")
        self.program = self.create_program()
        self.background = self.create_local_file(
            "background.jpg",
            b"template",
            extension="jpg",
            mime_type="image/jpeg",
        )
        self.template = ProgramCertificateTemplate.objects.create(
            program=self.program,
            is_enabled=True,
            release_mode=RELEASE_MODE_AFTER_PROGRAM_END,
            issue_condition_type=ISSUE_CONDITION_SUBMITTED_PROJECT,
            background_image=self.background,
        )

    def create_user(self, email: str, **extra_fields):
        defaults = {
            "password": "pass",
            "first_name": "Test",
            "last_name": "User",
            "birthday": "1990-01-01",
            "is_active": True,
        }
        defaults.update(extra_fields)
        return get_user_model().objects.create_user(email=email, **defaults)

    def create_program(self, **overrides):
        defaults = {
            "name": "Certificate generation program",
            "tag": f"certificate_generation_program_{PartnerProgram.objects.count()}",
            "description": "Program description",
            "city": "Moscow",
            "data_schema": {},
            "status": "published",
            "projects_availability": "all_users",
            "datetime_registration_ends": self.now - timezone.timedelta(days=20),
            "datetime_started": self.now - timezone.timedelta(days=10),
            "datetime_finished": self.now - timezone.timedelta(days=1),
        }
        defaults.update(overrides)
        program = PartnerProgram.objects.create(**defaults)
        program.managers.add(self.manager)
        return program

    def create_local_file(
        self,
        name="file.pdf",
        content=b"%PDF-1.4 test",
        *,
        extension="pdf",
        mime_type="application/pdf",
        user=None,
    ):
        self.file_index += 1
        relative_path = Path("certificates") / f"{self.file_index}-{name}"
        absolute_path = Path(settings.MEDIA_ROOT) / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_bytes(content)
        return UserFile.objects.create(
            link=(
                f"{settings.LOCAL_MEDIA_BASE_URL}"
                f"{settings.MEDIA_URL}{relative_path.as_posix()}"
            ),
            user=user or self.manager,
            name=Path(name).stem,
            extension=extension,
            mime_type=mime_type,
            size=len(content),
        )

    def make_upload_info(self, name="generated.pdf"):
        self.file_index += 1
        extension = Path(name).suffix.lstrip(".") or "pdf"
        return SimpleNamespace(
            url=f"https://cdn.test/certificates/{self.file_index}-{name}",
            name=Path(name).stem,
            extension=extension,
            mime_type="application/pdf",
            size=1024,
        )

    def register_user(self, user, *, submitted=True, project_name=None):
        project = Project.objects.create(
            leader=user,
            draft=False,
            is_public=False,
            name=project_name or f"Project {user.id}",
        )
        PartnerProgramUserProfile.objects.create(
            user=user,
            project=project,
            partner_program=self.program,
            partner_program_data={},
        )
        program_project = PartnerProgramProject.objects.create(
            partner_program=self.program,
            project=project,
            submitted=submitted,
            datetime_submitted=timezone.now() if submitted else None,
        )
        return project, program_project

    def create_certificate(self, user, program_project, *, pdf_file=None):
        return IssuedCertificate.objects.create(
            program=self.program,
            user=user,
            program_project=program_project,
            certificate_id=f"CERT-{self.program.id}-{user.id}-000001",
            pdf_file=pdf_file or self.create_local_file("issued.pdf", user=user),
            generated_at=timezone.now(),
        )

    def test_single_certificate_generation_creates_pdf_record(self):
        _, program_project = self.register_user(self.user_1, submitted=True)
        upload_info = self.make_upload_info("generated.pdf")

        with patch(
            "certificates.services.render_pdf_bytes",
            return_value=b"%PDF-1.4 generated",
        ), patch(
            "certificates.services.upload_certificate_pdf",
            return_value=upload_info,
        ):
            certificate = generate_certificate_for_user(
                program_id=self.program.id,
                user_id=self.user_1.id,
            )

        self.assertIsNotNone(certificate)
        self.assertEqual(certificate.program_project_id, program_project.id)
        self.assertEqual(certificate.pdf_file_id, upload_info.url)
        self.assertTrue(certificate.certificate_id.startswith("CERT-"))

    def test_recipients_use_only_submitted_project_rule(self):
        self.register_user(self.user_1, submitted=True)
        self.register_user(self.user_2, submitted=False)

        recipients = get_certificate_recipients(self.program, self.template)

        self.assertEqual([item.user_id for item in recipients], [self.user_1.id])

    def test_non_mvp_recipient_rules_return_no_recipients(self):
        self.register_user(self.user_1, submitted=True)

        for issue_condition in (
            ISSUE_CONDITION_ALL_REGISTERED,
            ISSUE_CONDITION_SCORE_THRESHOLD,
            ISSUE_CONDITION_TOP_POSITIONS,
        ):
            self.template.issue_condition_type = issue_condition
            self.template.save(update_fields=["issue_condition_type"])

            self.assertEqual(get_certificate_recipients(self.program, self.template), [])

    def test_repeated_generation_updates_existing_certificate_and_preserves_id(self):
        _, program_project = self.register_user(self.user_1, submitted=True)
        first_file = self.make_upload_info("first.pdf")
        second_file = self.make_upload_info("second.pdf")

        with patch(
            "certificates.services.render_pdf_bytes",
            return_value=b"%PDF-1.4 generated",
        ), patch(
            "certificates.services.upload_certificate_pdf",
            side_effect=[first_file, second_file],
        ):
            first_run = generate_certificates_for_program_sync(self.program)
            first = IssuedCertificate.objects.get(
                program=self.program,
                user=self.user_1,
                program_project=program_project,
            )
            first_certificate_id = first.certificate_id
            second_run = generate_certificates_for_program_sync(self.program)

        first.refresh_from_db()
        self.assertEqual(first_run.issued_count, 1)
        self.assertEqual(second_run.issued_count, 1)
        self.assertEqual(
            IssuedCertificate.objects.filter(
                program=self.program,
                user=self.user_1,
                program_project=program_project,
            ).count(),
            1,
        )
        self.assertEqual(first.certificate_id, first_certificate_id)
        self.assertEqual(first.pdf_file_id, second_file.url)

    def test_generation_without_template_is_skipped(self):
        program_without_template = self.create_program(tag="without_template")

        result = generate_certificates_for_program(program_without_template.id)

        self.assertEqual(result, 0)
        run = CertificateGenerationRun.objects.get(program=program_without_template)
        self.assertEqual(run.status, CertificateGenerationRun.STATUS_SKIPPED)

    @patch("certificates.tasks.generate_certificates_for_program.delay")
    def test_completion_transition_starts_generation_only_for_enabled_auto_mode(
        self,
        delay_mock,
    ):
        self.program.status = "completed"
        self.program.save()

        delay_mock.assert_called_once_with(self.program.id)

    @patch("certificates.tasks.generate_certificates_for_program.delay")
    def test_complete_finished_programs_task_completes_published_programs(
        self,
        delay_mock,
    ):
        completed_count = complete_finished_programs()

        self.assertEqual(completed_count, 1)
        self.program.refresh_from_db()
        self.assertEqual(self.program.status, "completed")
        delay_mock.assert_called_once_with(self.program.id)

    def test_my_certificate_endpoint_returns_scheduled_before_program_end(self):
        future_program = self.create_program(
            tag="future_certificate_program",
            datetime_finished=self.now + timezone.timedelta(days=2),
        )
        future_program.managers.add(self.manager)
        self.program = future_program
        self.template = ProgramCertificateTemplate.objects.create(
            program=future_program,
            is_enabled=True,
            release_mode=RELEASE_MODE_AFTER_PROGRAM_END,
            background_image=self.background,
        )
        _, program_project = self.register_user(self.user_1, submitted=True)
        self.create_certificate(self.user_1, program_project)

        request = self.factory.get(f"/programs/{future_program.id}/certificate/me/")
        force_authenticate(request, user=self.user_1)
        response = self.my_certificate_view(request, pk=future_program.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["state"], "scheduled")
        self.assertIsNone(response.data["certificate"])

    def test_manual_mode_requires_release_before_participant_access(self):
        self.template.release_mode = RELEASE_MODE_MANUAL
        self.template.save(update_fields=["release_mode"])
        _, program_project = self.register_user(self.user_1, submitted=True)
        certificate = self.create_certificate(self.user_1, program_project)

        request = self.factory.get(f"/programs/{self.program.id}/certificate/me/")
        force_authenticate(request, user=self.user_1)
        response = self.my_certificate_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["state"], "not_released")
        self.assertIsNone(response.data["certificate"])

        release_request = self.factory.post(
            f"/programs/{self.program.id}/certificate/release/"
        )
        force_authenticate(release_request, user=self.manager)
        release_response = self.release_view(release_request, pk=self.program.id)

        self.assertEqual(release_response.status_code, 200)
        self.template.refresh_from_db()
        self.assertIsNotNone(self.template.released_at)

        request = self.factory.get(f"/programs/{self.program.id}/certificate/me/")
        force_authenticate(request, user=self.user_1)
        response = self.my_certificate_view(request, pk=self.program.id)

        self.assertEqual(response.data["state"], "available")
        self.assertEqual(response.data["certificate"]["certificate_id"], certificate.certificate_id)

    def test_download_restrictions_respect_release_mode_and_owner(self):
        self.template.release_mode = RELEASE_MODE_MANUAL
        self.template.save(update_fields=["release_mode"])
        _, program_project = self.register_user(self.user_1, submitted=True)
        self.register_user(self.user_2, submitted=True)
        certificate = self.create_certificate(self.user_1, program_project)

        owner_request = self.factory.get(
            f"/programs/{self.program.id}/certificate/{certificate.certificate_id}/download/"
        )
        force_authenticate(owner_request, user=self.user_1)
        owner_response = self.download_view(
            owner_request,
            pk=self.program.id,
            certificate_id=certificate.certificate_id,
        )
        self.assertEqual(owner_response.status_code, 403)

        other_request = self.factory.get(
            f"/programs/{self.program.id}/certificate/{certificate.certificate_id}/download/"
        )
        force_authenticate(other_request, user=self.user_2)
        other_response = self.download_view(
            other_request,
            pk=self.program.id,
            certificate_id=certificate.certificate_id,
        )
        self.assertEqual(other_response.status_code, 403)

        manager_request = self.factory.get(
            f"/programs/{self.program.id}/certificate/{certificate.certificate_id}/download/"
        )
        force_authenticate(manager_request, user=self.manager)
        manager_response = self.download_view(
            manager_request,
            pk=self.program.id,
            certificate_id=certificate.certificate_id,
        )
        self.assertEqual(manager_response.status_code, 200)

        self.template.released_at = timezone.now()
        self.template.save(update_fields=["released_at"])
        owner_request = self.factory.get(
            f"/programs/{self.program.id}/certificate/{certificate.certificate_id}/download/"
        )
        force_authenticate(owner_request, user=self.user_1)
        owner_response = self.download_view(
            owner_request,
            pk=self.program.id,
            certificate_id=certificate.certificate_id,
        )
        self.assertEqual(owner_response.status_code, 200)

    def test_manager_can_list_certificates_and_outsider_cannot(self):
        _, program_project = self.register_user(self.user_1, submitted=True)
        self.create_certificate(self.user_1, program_project)

        request = self.factory.get(f"/programs/{self.program.id}/certificate/list/")
        force_authenticate(request, user=self.manager)
        response = self.list_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["certificates"]), 1)

        request = self.factory.get(f"/programs/{self.program.id}/certificate/list/")
        force_authenticate(request, user=self.outsider)
        response = self.list_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 403)

    def test_generation_stats_endpoint_returns_counts(self):
        _, first_program_project = self.register_user(self.user_1, submitted=True)
        self.register_user(self.user_2, submitted=True)
        self.create_certificate(self.user_1, first_program_project)
        CertificateGenerationRun.objects.create(
            program=self.program,
            status=CertificateGenerationRun.STATUS_COMPLETED,
            total_expected=2,
            enqueued_count=2,
            issued_count=1,
        )

        request = self.factory.get(
            f"/programs/{self.program.id}/certificate-template/stats/"
        )
        force_authenticate(request, user=self.manager)
        response = self.stats_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["generated_count"], 1)
        self.assertEqual(response.data["eligible_count"], 2)
        self.assertEqual(response.data["pending_count"], 1)
        self.assertEqual(response.data["last_run"]["status"], "completed")

    def test_team_members_are_rendered_from_project_owner_and_collaborators(self):
        owner = self.create_user(
            "certificate-owner@example.com",
            first_name="Иван",
            last_name="Петров",
        )
        collaborator = self.create_user(
            "certificate-collaborator@example.com",
            first_name="Мария",
            last_name="Сидорова",
        )
        self.program.managers.add(owner)
        project, program_project = self.register_user(
            owner,
            submitted=True,
            project_name="AI-модель оценки рисков",
        )
        PartnerProgramUserProfile.objects.create(
            user=collaborator,
            project=project,
            partner_program=self.program,
            partner_program_data={},
        )
        Collaborator.objects.create(project=project, user=collaborator)
        self.template.show_team_members = True
        positions = self.template.fields_positioning
        positions[FIELD_TEAM_MEMBERS]["visible"] = True
        self.template.fields_positioning = positions
        self.template.save(update_fields=["show_team_members", "fields_positioning"])

        html = render_certificate_html(
            program=self.program,
            template=self.template,
            recipient=CertificateRecipient(
                user_id=owner.id,
                program_project_id=program_project.id,
                project_id=project.id,
            ),
            certificate_id="CERT-TEST",
        )

        self.assertIn("Петров Иван", html)
        self.assertIn("Сидорова Мария", html)
        self.assertNotIn("team_name", html)

    def test_admin_can_delete_certificate_and_file_record(self):
        _, program_project = self.register_user(self.user_1, submitted=True)
        pdf_file = self.create_local_file("delete-me.pdf", user=self.user_1)
        certificate = self.create_certificate(
            self.user_1,
            program_project,
            pdf_file=pdf_file,
        )

        request = self.factory.delete(f"/api/admin/certificates/{certificate.id}/")
        force_authenticate(request, user=self.admin)
        response = self.delete_view(request, pk=certificate.id)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(IssuedCertificate.objects.filter(pk=certificate.id).exists())
        self.assertFalse(UserFile.objects.filter(pk=pdf_file.pk).exists())
