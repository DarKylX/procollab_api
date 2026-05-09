from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from partner_programs.models import PartnerProgram
from partner_programs.services import validate_project_team_size_for_program
from projects.models import Collaborator, Project

User = get_user_model()


class ProgramProjectParticipationRuleTests(TestCase):
    def setUp(self):
        self.leader = User.objects.create_user(
            email="leader-rules@example.com",
            password="pass",
            first_name="Leader",
            last_name="Rules",
            birthday="1990-01-01",
            is_active=True,
        )
        self.member = User.objects.create_user(
            email="member-rules@example.com",
            password="pass",
            first_name="Member",
            last_name="Rules",
            birthday="1991-01-01",
            is_active=True,
        )
        self.project = Project.objects.create(
            leader=self.leader,
            draft=True,
            is_public=False,
            name="Project",
        )

    def create_program(self, **overrides):
        now = timezone.now()
        defaults = {
            "name": "Program",
            "tag": "program",
            "description": "Program description",
            "city": "Moscow",
            "datetime_registration_ends": now + timezone.timedelta(days=2),
            "datetime_started": now + timezone.timedelta(days=1),
            "datetime_finished": now + timezone.timedelta(days=10),
        }
        defaults.update(overrides)
        return PartnerProgram.objects.create(**defaults)

    def test_individual_format_rejects_project_with_collaborators(self):
        Collaborator.objects.create(project=self.project, user=self.member)
        program = self.create_program(
            participation_format=PartnerProgram.PARTICIPATION_FORMAT_INDIVIDUAL
        )

        with self.assertRaises(ValueError):
            validate_project_team_size_for_program(program=program, project=self.project)

    def test_team_format_applies_min_and_max_to_existing_project_team(self):
        Collaborator.objects.create(project=self.project, user=self.member)
        program = self.create_program(
            participation_format=PartnerProgram.PARTICIPATION_FORMAT_TEAM,
            project_team_min_size=2,
            project_team_max_size=3,
        )

        validate_project_team_size_for_program(program=program, project=self.project)

        program.project_team_max_size = 1
        with self.assertRaises(ValueError):
            validate_project_team_size_for_program(program=program, project=self.project)
