from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from certificates.models import IssuedCertificate, ProgramCertificateTemplate
from certificates.services import CertificateRecipient, render_certificate_html
from files.models import UserFile
from partner_programs.models import PartnerProgram
from projects.models import Company


@override_settings(
    DEBUG=False,
    FRONTEND_URL="https://procollab.ru",
)
class PublicCertificateVerificationTests(TestCase):
    def setUp(self):
        self.api_client = APIClient()
        self.html_client = Client()
        self.now = timezone.now()
        self.user = self.create_user(
            "certificate-owner@example.com",
            first_name="Иван",
            last_name="Петров",
            patronymic="Сергеевич",
            phone_number="+79990000000",
        )
        self.company = Company.objects.create(name="ООО Ромашка", inn="7707083893")
        self.program = self.create_program(
            company=self.company,
            verification_status="verified",
        )
        self.pdf_file = self.create_file()
        self.certificate = IssuedCertificate.objects.create(
            program=self.program,
            user=self.user,
            team_name="Команда Альфа",
            final_score=Decimal("95.50"),
            rating_position=2,
            pdf_file=self.pdf_file,
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
            "name": "Certificate verification program",
            "tag": f"certificate_verification_{PartnerProgram.objects.count()}",
            "description": "Program description",
            "city": "Moscow",
            "data_schema": {},
            "status": "completed",
            "projects_availability": "all_users",
            "datetime_registration_ends": self.now - timezone.timedelta(days=20),
            "datetime_started": self.now - timezone.timedelta(days=10),
            "datetime_finished": self.now - timezone.timedelta(days=1),
        }
        defaults.update(overrides)
        return PartnerProgram.objects.create(**defaults)

    def create_file(self, name="certificate.pdf"):
        return UserFile.objects.create(
            link=f"https://cdn.test/certificates/{name}",
            user=self.user,
            name=name.removesuffix(".pdf"),
            extension="pdf",
            mime_type="application/pdf",
            size=1024,
        )

    def api_url(self, certificate_uuid):
        return reverse(
            "certificates:api-public-certificate-verify",
            kwargs={"certificate_uuid": certificate_uuid},
        )

    def html_url(self, certificate_uuid):
        return reverse(
            "certificates:public-certificate-verify",
            kwargs={"certificate_uuid": certificate_uuid},
        )

    def test_api_returns_certificate_verification_data(self):
        response = self.api_client.get(self.api_url(self.certificate.certificate_uuid))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_valid"])
        self.assertEqual(response.data["participant_full_name"], "Петров Иван Сергеевич")
        self.assertEqual(response.data["program_name"], self.program.name)
        self.assertEqual(response.data["organizer_name"], self.company.name)
        self.assertTrue(response.data["is_organizer_verified"])
        self.assertEqual(response.data["team_name"], "Команда Альфа")
        self.assertEqual(response.data["rating_position"], 2)
        self.assertEqual(response.data["final_score"], "95.50")

    def test_api_returns_404_for_unknown_uuid(self):
        response = self.api_client.get(self.api_url(uuid4()))

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.data["is_valid"])
        self.assertIn("не найден", response.data["detail"])

    def test_api_returns_400_for_invalid_uuid(self):
        response = self.api_client.get(self.api_url("not-a-uuid"))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["is_valid"])
        self.assertIn("формат", response.data["detail"])

    def test_api_is_public_and_does_not_expose_private_user_data(self):
        response = self.api_client.get(self.api_url(self.certificate.certificate_uuid))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        forbidden_keys = {"email", "phone", "phone_number", "birthday", "user", "id"}
        self.assertTrue(forbidden_keys.isdisjoint(payload.keys()))
        self.assertNotIn(self.user.email, response.content.decode("utf-8"))
        self.assertNotIn(self.user.phone_number, response.content.decode("utf-8"))

    def test_html_page_returns_valid_certificate_details(self):
        response = self.html_client.get(self.html_url(self.certificate.certificate_uuid))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("Проверка подлинности сертификата", html)
        self.assertIn("Сертификат действителен", html)
        self.assertIn("Петров Иван Сергеевич", html)
        self.assertIn(self.program.name, html)
        self.assertIn(
            timezone.localtime(self.program.datetime_finished).strftime("%d.%m.%Y"),
            html,
        )
        self.assertIn('name="robots" content="noindex, nofollow"', html)

    def test_html_page_returns_error_for_unknown_uuid(self):
        response = self.html_client.get(self.html_url(uuid4()))

        self.assertEqual(response.status_code, 404)
        html = response.content.decode("utf-8")
        self.assertIn("Сертификат не найден", html)
        self.assertIn("не найден", html)

    def test_organizer_verified_flag_is_false_without_verified_program(self):
        unverified_program = self.create_program(
            tag="certificate_verification_unverified",
            company=None,
            verification_status="not_requested",
        )
        certificate = IssuedCertificate.objects.create(
            program=unverified_program,
            user=self.user,
            pdf_file=self.create_file("unverified.pdf"),
        )

        response = self.api_client.get(self.api_url(certificate.certificate_uuid))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_organizer_verified"])
        self.assertNotIn("organizer_name", response.data)

    def test_optional_fields_are_omitted_when_empty(self):
        certificate = IssuedCertificate.objects.create(
            program=self.program,
            user=self.create_user("certificate-no-optionals@example.com"),
            pdf_file=self.create_file("without-optionals.pdf"),
        )

        response = self.api_client.get(self.api_url(certificate.certificate_uuid))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("team_name", response.data)
        self.assertNotIn("rating_position", response.data)
        self.assertNotIn("final_score", response.data)

    def test_pdf_certificate_html_does_not_show_public_verification_link(self):
        template = ProgramCertificateTemplate.objects.create(program=self.program)

        html = render_certificate_html(
            program=self.program,
            template=template,
            recipient=CertificateRecipient(user_id=self.user.id),
            certificate_uuid=self.certificate.certificate_uuid,
        )

        self.assertNotIn(
            f"https://procollab.ru/certificates/verify/{self.certificate.certificate_uuid}/",
            html,
        )
        self.assertNotIn("Проверить подлинность", html)
