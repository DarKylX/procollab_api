from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from partner_programs.models import (
    PartnerProgram,
    PartnerProgramInvite,
    PartnerProgramUserProfile,
)


@override_settings(
    DEBUG=False,
    FRONTEND_URL="https://procollab.ru",
    DEFAULT_FROM_EMAIL="from@test",
)
class PartnerProgramInviteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.now = timezone.now()
        self.manager = self.create_user("manager-invites@example.com")
        self.outsider = self.create_user("outsider-invites@example.com")
        self.participant = self.create_user("participant-invites@example.com")
        self.program = self.create_program(is_private=True)
        self.program.managers.add(self.manager)
        self.open_program = self.create_program(
            tag="open_invites_program",
            name="Open invites program",
            is_private=False,
        )
        self.open_program.managers.add(self.manager)

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
            "name": "Private invites program",
            "tag": "private_invites_program",
            "description": "Private program description",
            "city": "Moscow",
            "data_schema": {},
            "status": "published",
            "projects_availability": "all_users",
            "datetime_registration_ends": self.now + timezone.timedelta(days=10),
            "datetime_started": self.now + timezone.timedelta(days=20),
            "datetime_finished": self.now + timezone.timedelta(days=50),
            "is_private": True,
        }
        defaults.update(overrides)
        return PartnerProgram.objects.create(**defaults)

    def program_invites_url(self, program):
        return f"/api/partner-programs/{program.id}/invites/"

    def invite_detail_url(self, invite):
        return f"/api/invites/{invite.token}/"

    def invite_accept_url(self, invite):
        return f"/api/invites/{invite.token}/accept/"

    def create_invite(self, **overrides):
        defaults = {
            "program": self.program,
            "email": "invited@example.com",
            "created_by": self.manager,
            "expires_at": self.now + timezone.timedelta(days=30),
        }
        defaults.update(overrides)
        return PartnerProgramInvite.objects.create(**defaults)

    @patch("partner_programs.services.send_mail", return_value=1)
    def test_manager_can_create_single_invite_and_email_is_sent(self, send_mail_mock):
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            self.program_invites_url(self.program),
            {"email": "Invited@Example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data), 1)
        invite = PartnerProgramInvite.objects.get()
        self.assertEqual(invite.email, "invited@example.com")
        self.assertEqual(invite.status, PartnerProgramInvite.STATUS_PENDING)
        self.assertIn(str(invite.token), response.data[0]["accept_url"])
        send_mail_mock.assert_called_once()
        email_text = send_mail_mock.call_args.kwargs["message"]
        self.assertIn(str(invite.token), email_text)
        self.assertIn("https://procollab.ru/invite/", email_text)

    @patch("partner_programs.services.send_mail", return_value=1)
    def test_manager_can_create_bulk_invites(self, send_mail_mock):
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            self.program_invites_url(self.program),
            {"emails": ["one@example.com", "two@example.com"]},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(PartnerProgramInvite.objects.count(), 2)
        self.assertEqual(send_mail_mock.call_count, 2)

    @patch("partner_programs.services.send_mail", return_value=1)
    def test_invite_creation_for_open_program_returns_400(self, _send_mail_mock):
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            self.program_invites_url(self.open_program),
            {"email": "invited@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_non_manager_cannot_create_invites(self):
        self.client.force_authenticate(self.outsider)

        response = self.client.post(
            self.program_invites_url(self.program),
            {"email": "invited@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_public_invite_detail_is_available_without_auth(self):
        invite = self.create_invite()

        response = self.client.get(self.invite_detail_url(invite))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["program_id"], self.program.id)
        self.assertEqual(response.data["program_name"], self.program.name)

    def test_public_invite_detail_returns_404_for_unknown_token(self):
        response = self.client.get(f"/api/invites/{uuid4()}/")

        self.assertEqual(response.status_code, 404)

    def test_public_invite_detail_returns_410_for_expired_invite(self):
        invite = self.create_invite(expires_at=self.now - timezone.timedelta(days=1))

        response = self.client.get(self.invite_detail_url(invite))

        self.assertEqual(response.status_code, 410)
        invite.refresh_from_db()
        self.assertEqual(invite.status, PartnerProgramInvite.STATUS_EXPIRED)

    def test_public_invite_detail_returns_410_for_used_invite(self):
        invite = self.create_invite(
            status=PartnerProgramInvite.STATUS_USED,
            accepted_by=self.participant,
            accepted_at=self.now,
        )

        response = self.client.get(self.invite_detail_url(invite))

        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.data["status"], PartnerProgramInvite.STATUS_USED)

    def test_authenticated_user_can_accept_invite(self):
        invite = self.create_invite()
        self.client.force_authenticate(self.participant)

        response = self.client.post(self.invite_accept_url(invite))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["program_id"], self.program.id)
        self.assertTrue(
            PartnerProgramUserProfile.objects.filter(
                partner_program=self.program,
                user=self.participant,
            ).exists()
        )
        invite.refresh_from_db()
        self.assertEqual(invite.status, PartnerProgramInvite.STATUS_USED)
        self.assertEqual(invite.accepted_by, self.participant)
        self.assertIsNotNone(invite.accepted_at)

    def test_repeated_accept_returns_410(self):
        invite = self.create_invite()
        self.client.force_authenticate(self.participant)
        self.client.post(self.invite_accept_url(invite))

        response = self.client.post(self.invite_accept_url(invite))

        self.assertEqual(response.status_code, 410)

    def test_unauthenticated_accept_requires_authentication(self):
        invite = self.create_invite()

        response = self.client.post(self.invite_accept_url(invite))

        self.assertIn(response.status_code, (401, 403))

    def test_manager_can_list_invites_and_filter_by_status(self):
        pending_invite = self.create_invite(email="pending@example.com")
        self.create_invite(
            email="revoked@example.com",
            status=PartnerProgramInvite.STATUS_REVOKED,
        )
        self.client.force_authenticate(self.manager)

        response = self.client.get(
            self.program_invites_url(self.program),
            {"status": PartnerProgramInvite.STATUS_PENDING},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], pending_invite.id)

    def test_manager_can_revoke_invite_and_revoked_invite_cannot_be_used(self):
        invite = self.create_invite()
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            f"/api/partner-programs/{self.program.id}/invites/{invite.id}/revoke/"
        )

        self.assertEqual(response.status_code, 200)
        invite.refresh_from_db()
        self.assertEqual(invite.status, PartnerProgramInvite.STATUS_REVOKED)

        self.client.force_authenticate(self.participant)
        accept_response = self.client.post(self.invite_accept_url(invite))
        self.assertEqual(accept_response.status_code, 410)

    @patch("partner_programs.services.send_mail", return_value=1)
    def test_manager_can_resend_invite(self, send_mail_mock):
        invite = self.create_invite()
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            f"/api/partner-programs/{self.program.id}/invites/{invite.id}/resend/",
            {"expires_in_days": 45},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        send_mail_mock.assert_called_once()
        invite.refresh_from_db()
        self.assertGreater(invite.expires_at, self.now + timezone.timedelta(days=40))

    def test_manager_can_delete_revoked_invite(self):
        invite = self.create_invite(status=PartnerProgramInvite.STATUS_REVOKED)
        self.client.force_authenticate(self.manager)

        response = self.client.delete(
            f"/api/partner-programs/{self.program.id}/invites/{invite.id}/"
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(PartnerProgramInvite.objects.filter(pk=invite.pk).exists())

    def test_private_program_is_hidden_from_public_list(self):
        response = self.client.get("/programs/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.program.name, response.content.decode("utf-8"))

    def test_private_program_detail_for_outsider_returns_404(self):
        self.client.force_authenticate(self.outsider)

        response = self.client.get(f"/programs/{self.program.id}/")

        self.assertEqual(response.status_code, 404)

    def test_private_program_detail_for_participant_is_available(self):
        PartnerProgramUserProfile.objects.create(
            partner_program=self.program,
            user=self.participant,
            partner_program_data={},
        )
        self.client.force_authenticate(self.participant)

        response = self.client.get(f"/programs/{self.program.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.program.id)

    def test_invite_page_returns_html(self):
        invite = self.create_invite()

        response = self.client.get(f"/invite/{invite.token}/")

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("Приглашение в закрытый чемпионат", html)
        self.assertIn(self.program.name, html)
