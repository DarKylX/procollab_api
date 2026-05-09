import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIRequestFactory, force_authenticate

from certificates.enums import (
    FIELD_CERTIFICATE_ID,
    FIELD_PROJECT_TITLE,
    get_default_fields_positioning,
)
from certificates.models import ProgramCertificateTemplate
from certificates.views import (
    CertificateFontListView,
    ProgramCertificateLegacyTemplateView,
    ProgramCertificateTemplatePreviewView,
    ProgramCertificateTemplateView,
)
from files.models import UserFile
from partner_programs.models import PartnerProgram

TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="certificates-tests-"))


@override_settings(
    MEDIA_ROOT=TEST_MEDIA_ROOT,
    LOCAL_MEDIA_BASE_URL="http://127.0.0.1:8000",
)
class ProgramCertificateTemplateTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.factory = APIRequestFactory()
        self.template_view = ProgramCertificateTemplateView.as_view()
        self.legacy_template_view = ProgramCertificateLegacyTemplateView.as_view()
        self.preview_view = ProgramCertificateTemplatePreviewView.as_view()
        self.fonts_view = CertificateFontListView.as_view()
        self.now = timezone.now()
        self.file_index = 0

        self.manager = self.create_user("certificate-manager@example.com")
        self.outsider = self.create_user("certificate-outsider@example.com")
        self.program = self.create_program()

    def create_user(self, email: str, **extra_fields):
        return get_user_model().objects.create_user(
            email=email,
            password="pass",
            first_name="Test",
            last_name="User",
            birthday="1990-01-01",
            **extra_fields,
        )

    def create_program(self, **overrides):
        defaults = {
            "name": "Certificate program",
            "tag": "certificate_program",
            "description": "Program description",
            "city": "Moscow",
            "data_schema": {},
            "status": "published",
            "projects_availability": "all_users",
            "datetime_registration_ends": self.now + timezone.timedelta(days=10),
            "datetime_started": self.now + timezone.timedelta(days=20),
            "datetime_finished": self.now + timezone.timedelta(days=50),
        }
        defaults.update(overrides)
        program = PartnerProgram.objects.create(**defaults)
        program.managers.add(self.manager)
        return program

    def create_image_file(self, size=(900, 700), extension="jpg", **overrides):
        self.file_index += 1
        filename = f"template-{self.file_index}.{extension}"
        relative_path = Path("certificates") / filename
        absolute_path = Path(settings.MEDIA_ROOT) / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)

        image_format = "PNG" if extension == "png" else "JPEG"
        Image.new("RGB", size, color=(245, 245, 245)).save(
            absolute_path, format=image_format
        )

        defaults = {
            "link": (
                f"{settings.LOCAL_MEDIA_BASE_URL}"
                f"{settings.MEDIA_URL}{relative_path.as_posix()}"
            ),
            "user": self.manager,
            "name": filename.removesuffix(f".{extension}"),
            "extension": extension,
            "mime_type": "image/png" if extension == "png" else "image/jpeg",
            "size": absolute_path.stat().st_size,
        }
        defaults.update(overrides)
        return UserFile.objects.create(**defaults)

    def create_metadata_file(self, index: int, **overrides):
        defaults = {
            "link": f"https://cdn.test/certificates/template-{index}.jpg",
            "user": self.manager,
            "name": f"template-{index}",
            "extension": "jpg",
            "mime_type": "image/jpeg",
            "size": 1024,
        }
        defaults.update(overrides)
        return UserFile.objects.create(**defaults)

    def create_uploaded_image(self, size=(900, 700)):
        buffer = BytesIO()
        Image.new("RGB", size, color=(245, 245, 245)).save(buffer, format="JPEG")
        buffer.seek(0)
        return SimpleUploadedFile(
            "template.jpg",
            buffer.getvalue(),
            content_type="image/jpeg",
        )

    def test_manager_can_create_template_with_minimal_fields(self):
        background = self.create_image_file()

        request = self.factory.put(
            f"/programs/{self.program.id}/certificate-template/",
            {"background_image": background.link},
            format="json",
        )
        force_authenticate(request, user=self.manager)
        response = self.template_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 201)
        template = ProgramCertificateTemplate.objects.get(program=self.program)
        self.assertEqual(template.background_image_id, background.link)
        self.assertEqual(template.font_family, "roboto")
        self.assertIn("participant_full_name", template.fields_positioning)

    @patch("certificates.serializers.upload_background_image")
    def test_manager_can_upload_background_image_with_multipart_alias(self, upload_mock):
        stored_background = self.create_metadata_file(10)
        upload_mock.return_value = stored_background

        request = self.factory.put(
            f"/programs/{self.program.id}/certificate-template/",
            {"background_image": self.create_uploaded_image()},
            format="multipart",
        )
        force_authenticate(request, user=self.manager)
        response = self.template_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["background_image"], stored_background.link)
        upload_mock.assert_called_once()

    def test_manager_can_save_signature_and_stamp_assets(self):
        background = self.create_image_file()
        signature = self.create_image_file(extension="png")
        stamp = self.create_image_file(extension="png")
        company_logo = self.create_image_file(extension="png")

        request = self.factory.put(
            f"/programs/{self.program.id}/certificate-template/",
            {
                "background_file": background.link,
                "signature_file": signature.link,
                "stamp_file": stamp.link,
                "company_logo_file": company_logo.link,
            },
            format="json",
        )
        force_authenticate(request, user=self.manager)
        response = self.template_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 201)
        template = ProgramCertificateTemplate.objects.get(program=self.program)
        self.assertEqual(template.signature_image_id, signature.link)
        self.assertEqual(template.stamp_image_id, stamp.link)
        self.assertEqual(template.company_logo_image_id, company_logo.link)
        self.assertEqual(response.data["signature_file"], signature.link)
        self.assertEqual(response.data["stamp_file"], stamp.link)
        self.assertEqual(response.data["company_logo_file"], company_logo.link)

    def test_manager_can_save_template_with_default_background_and_asset_layout(self):
        request = self.factory.put(
            f"/programs/{self.program.id}/certificate-template/",
            {
                "is_enabled": True,
                "signer_name": "Анна Смирнова",
                "signature_position": {"x": 0.72, "y": 0.77, "width": 0.18},
                "stamp_position": {"x": 0.43, "y": 0.80, "width": 0.13},
            },
            format="json",
        )
        force_authenticate(request, user=self.manager)
        response = self.template_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 201)
        template = ProgramCertificateTemplate.objects.get(program=self.program)
        self.assertIsNone(template.background_image_id)
        self.assertTrue(response.data["is_configured"])
        self.assertEqual(template.signer_name, "Анна Смирнова")
        self.assertEqual(template.signature_position["width"], 0.18)

    def test_manager_can_patch_template_fields(self):
        background = self.create_image_file()
        ProgramCertificateTemplate.objects.create(
            program=self.program,
            background_image=background,
        )

        request = self.factory.patch(
            f"/programs/{self.program.id}/certificate-template/",
            {"font_family": "manrope", "accent_text_color": "#336699"},
            format="json",
        )
        force_authenticate(request, user=self.manager)
        response = self.template_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 200)
        self.program.certificate_template.refresh_from_db()
        self.assertEqual(self.program.certificate_template.font_family, "manrope")
        self.assertEqual(self.program.certificate_template.accent_text_color, "#336699")

    def test_outsider_cannot_create_template(self):
        background = self.create_image_file()

        request = self.factory.put(
            f"/programs/{self.program.id}/certificate-template/",
            {"background_image": background.link},
            format="json",
        )
        force_authenticate(request, user=self.outsider)
        response = self.template_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 403)

    def test_invalid_background_format_returns_400(self):
        background = self.create_metadata_file(
            1,
            extension="gif",
            mime_type="image/gif",
        )

        request = self.factory.put(
            f"/programs/{self.program.id}/certificate-template/",
            {"background_image": background.link},
            format="json",
        )
        force_authenticate(request, user=self.manager)
        response = self.template_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn("background_image", response.data)

    def test_large_background_returns_400(self):
        background = self.create_metadata_file(2, size=10 * 1024 * 1024 + 1)

        request = self.factory.put(
            f"/programs/{self.program.id}/certificate-template/",
            {"background_image": background.link},
            format="json",
        )
        force_authenticate(request, user=self.manager)
        response = self.template_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn("background_image", response.data)

    def test_small_background_dimensions_returns_400(self):
        background = self.create_image_file(size=(799, 600))

        request = self.factory.put(
            f"/programs/{self.program.id}/certificate-template/",
            {"background_image": background.link},
            format="json",
        )
        force_authenticate(request, user=self.manager)
        response = self.template_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn("background_image", response.data)

    def test_font_list_returns_available_fonts(self):
        request = self.factory.get("/api/certificates/fonts/")
        force_authenticate(request, user=self.manager)
        response = self.fonts_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 4)
        self.assertIn("id", response.data[0])
        self.assertIn("label", response.data[0])

    def test_preview_returns_html_with_test_data(self):
        background = self.create_image_file()

        request = self.factory.post(
            f"/programs/{self.program.id}/certificate-template/preview/",
            {"background_image": background.link},
            format="json",
        )
        force_authenticate(request, user=self.manager)
        response = self.preview_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html; charset=utf-8")
        html = response.content.decode("utf-8")
        self.assertIn("Иван Петров", html)
        self.assertIn("Финансовый форсайт 2026", html)
        self.assertIn("AI-модель оценки рисков", html)
        self.assertIn("CERT-2026-000124", html)

    def test_preview_without_background_uses_default_certificate_layout(self):
        request = self.factory.post(
            f"/programs/{self.program.id}/certificate-template/preview/",
            {"signer_name": "Анна Смирнова"},
            format="json",
        )
        force_authenticate(request, user=self.manager)
        response = self.preview_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("default-frame", html)
        self.assertIn("Анна Смирнова", html)

    def test_preview_hides_certificate_id_label_when_field_is_hidden(self):
        fields = get_default_fields_positioning()
        fields[FIELD_CERTIFICATE_ID]["visible"] = False

        request = self.factory.post(
            f"/programs/{self.program.id}/certificate-template/preview/",
            {"field_positions": fields},
            format="json",
        )
        force_authenticate(request, user=self.manager)
        response = self.preview_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertNotIn("CERT-2026-000124", html)
        self.assertNotIn(
            'class="default-bottom-label default-bottom-label--id"',
            html,
        )

    def test_project_label_is_rendered_with_project_title(self):
        fields = get_default_fields_positioning()
        fields[FIELD_PROJECT_TITLE].update({"x": 0.62, "y": 0.66})

        request = self.factory.post(
            f"/programs/{self.program.id}/certificate-template/preview/",
            {"field_positions": fields},
            format="json",
        )
        force_authenticate(request, user=self.manager)
        response = self.preview_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("certificate-field--project-label", html)
        self.assertIn("Проект", html)
        self.assertIn("AI-модель оценки рисков", html)
        self.assertIn("left: 62.0000%; top: 62.0000%", html)

    def test_delete_template_without_issued_certificates(self):
        background = self.create_image_file()
        ProgramCertificateTemplate.objects.create(
            program=self.program,
            background_image=background,
        )

        request = self.factory.delete(
            f"/programs/{self.program.id}/certificate-template/"
        )
        force_authenticate(request, user=self.manager)
        response = self.template_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            ProgramCertificateTemplate.objects.filter(program=self.program).exists()
        )

    def test_nonexistent_program_returns_404(self):
        request = self.factory.get("/programs/999999/certificate-template/")
        force_authenticate(request, user=self.manager)
        response = self.template_view(request, pk=999999)

        self.assertEqual(response.status_code, 404)

    def test_program_without_template_returns_default_settings(self):
        request = self.factory.get(f"/programs/{self.program.id}/certificate-template/")
        force_authenticate(request, user=self.manager)
        response = self.template_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_enabled"])
        self.assertFalse(response.data["is_configured"])

    def test_legacy_template_endpoint_without_template_returns_404(self):
        request = self.factory.get(f"/programs/{self.program.id}/certificate-template/")
        force_authenticate(request, user=self.manager)
        response = self.legacy_template_view(request, pk=self.program.id)

        self.assertEqual(response.status_code, 404)
