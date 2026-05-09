from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient

from partner_programs.models import PartnerProgram, PartnerProgramProject
from projects.models import Collaborator, Project, ProjectLink
from project_rates.models import (
    Criteria,
    ProjectEvaluation,
    ProjectEvaluationScore,
    ProjectExpertAssignment,
)
from users.models import CustomUser


class ExpertProjectEvaluationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        now = timezone.now()
        self.program = PartnerProgram.objects.create(
            name="Financial Foresight 2026",
            tag="finance",
            description="Program description",
            city="Moscow",
            data_schema={},
            draft=False,
            status="published",
            is_competitive=True,
            projects_availability="all_users",
            datetime_registration_ends=now + timezone.timedelta(days=5),
            datetime_project_submission_ends=now + timezone.timedelta(days=10),
            datetime_evaluation_ends=now + timezone.timedelta(days=15),
            datetime_started=now - timezone.timedelta(days=1),
            datetime_finished=now + timezone.timedelta(days=30),
        )
        self.expert_user = CustomUser.objects.create_user(
            email="expert-eval@example.com",
            password="pass",
            first_name="Expert",
            last_name="One",
            birthday="1990-01-01",
            user_type=CustomUser.EXPERT,
            is_active=True,
        )
        self.other_expert_user = CustomUser.objects.create_user(
            email="other-expert-eval@example.com",
            password="pass",
            first_name="Expert",
            last_name="Two",
            birthday="1990-01-02",
            user_type=CustomUser.EXPERT,
            is_active=True,
        )
        self.member_user = CustomUser.objects.create_user(
            email="member-eval@example.com",
            password="pass",
            first_name="Member",
            last_name="User",
            birthday="1992-01-01",
            user_type=CustomUser.MEMBER,
            is_active=True,
        )
        self.manager_user = CustomUser.objects.create_user(
            email="manager-eval@example.com",
            password="pass",
            first_name="Manager",
            last_name="Owner",
            birthday="1988-01-01",
            user_type=CustomUser.MEMBER,
            is_active=True,
        )
        self.collaborator_user = CustomUser.objects.create_user(
            email="collab-eval@example.com",
            password="pass",
            first_name="Collab",
            last_name="User",
            birthday="1993-01-01",
            user_type=CustomUser.MEMBER,
            is_active=True,
        )
        self.staff_user = CustomUser.objects.create_user(
            email="staff-eval@example.com",
            password="pass",
            first_name="Staff",
            last_name="User",
            birthday="1985-01-01",
            user_type=CustomUser.MEMBER,
            is_staff=True,
            is_active=True,
        )
        self.expert_user.expert.programs.add(self.program)
        self.other_expert_user.expert.programs.add(self.program)
        self.program.managers.add(self.manager_user)

        self.project = Project.objects.create(
            leader=self.member_user,
            draft=False,
            is_public=False,
            name="Risk Model",
            description="Project description",
            presentation_address="https://example.com/presentation.pdf",
        )
        Collaborator.objects.create(project=self.project, user=self.collaborator_user)
        ProjectLink.objects.create(project=self.project, link="https://example.com/repo")
        self.link = PartnerProgramProject.objects.create(
            partner_program=self.program,
            project=self.project,
            submitted=True,
            datetime_submitted=now,
        )

        self.other_project = Project.objects.create(
            leader=self.member_user,
            draft=False,
            is_public=False,
            name="Budget Assistant",
        )
        self.other_link = PartnerProgramProject.objects.create(
            partner_program=self.program,
            project=self.other_project,
            submitted=True,
            datetime_submitted=now,
        )

        self.unsubmitted_project = Project.objects.create(
            leader=self.member_user,
            draft=False,
            is_public=False,
            name="Unsubmitted",
        )
        self.unsubmitted_link = PartnerProgramProject.objects.create(
            partner_program=self.program,
            project=self.unsubmitted_project,
            submitted=False,
        )

        self.criteria_impact = Criteria.objects.create(
            name="Impact",
            description="Impact description",
            type="int",
            min_value=1,
            max_value=10,
            weight=50,
            partner_program=self.program,
        )
        self.criteria_quality = Criteria.objects.create(
            name="Quality",
            description="Quality description",
            type="float",
            min_value=1,
            max_value=5,
            weight=50,
            partner_program=self.program,
        )
        self.criteria_comment = Criteria.objects.create(
            name="Comment",
            description="Comment description",
            type="str",
            weight=1,
            partner_program=self.program,
        )

    def list_url(self):
        return f"/rate-project/{self.program.id}/submissions/"

    def detail_url(self, link_id=None):
        return f"/rate-project/{self.program.id}/submissions/{link_id or self.link.id}/"

    def draft_url(self):
        return f"/rate-project/{self.program.id}/submissions/{self.link.id}/draft/"

    def submit_url(self):
        return f"/rate-project/{self.program.id}/submissions/{self.link.id}/submit/"

    def expert_programs_url(self):
        return "/rate-project/expert/evaluations/"

    def test_expert_program_entry_returns_program_summaries_and_counters(self):
        ProjectEvaluation.objects.create(
            program_project=self.link,
            user=self.expert_user,
            status=ProjectEvaluation.STATUS_SUBMITTED,
            total_score=Decimal("8.00"),
            submitted_at=timezone.now(),
        )
        self.client.force_authenticate(self.expert_user)

        response = self.client.get(self.expert_programs_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        summary = response.data[0]
        self.assertEqual(summary["id"], self.program.id)
        self.assertEqual(summary["assigned"], 2)
        self.assertEqual(summary["evaluated"], 1)
        self.assertEqual(summary["remaining"], 1)
        self.assertEqual(summary["stage"], "Expert evaluation")
        self.assertEqual(summary["stage_status"], "Evaluation in progress")

    def test_expert_program_entry_respects_distributed_assignment_scope(self):
        self.program.is_distributed_evaluation = True
        self.program.save(update_fields=["is_distributed_evaluation"])
        self.client.force_authenticate(self.expert_user)

        empty_response = self.client.get(self.expert_programs_url())
        self.assertEqual(empty_response.status_code, 200)
        self.assertEqual(empty_response.data, [])

        ProjectExpertAssignment.objects.create(
            partner_program=self.program,
            project=self.project,
            expert=self.expert_user.expert,
        )

        response = self.client.get(self.expert_programs_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["assigned"], 1)

    def test_non_expert_program_entry_returns_empty_list(self):
        self.client.force_authenticate(self.member_user)

        response = self.client.get(self.expert_programs_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_staff_program_entry_returns_submitted_programs(self):
        self.client.force_authenticate(self.staff_user)

        response = self.client.get(self.expert_programs_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["assigned"], 2)

    def test_manager_program_entry_returns_managed_programs_without_expert_role(self):
        self.client.force_authenticate(self.manager_user)

        response = self.client.get(self.expert_programs_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.program.id)
        self.assertEqual(response.data[0]["assigned"], 2)

    def test_list_returns_only_submitted_projects_for_program_expert(self):
        self.client.force_authenticate(self.expert_user)

        response = self.client.get(self.list_url())

        self.assertEqual(response.status_code, 200)
        returned_ids = {item["id"] for item in response.data["results"]}
        self.assertSetEqual(returned_ids, {self.link.id, self.other_link.id})
        self.assertEqual(response.data["counters"]["assigned"], 2)
        self.assertEqual(response.data["counters"]["evaluated"], 0)
        self.assertEqual(response.data["counters"]["remaining"], 2)

    def test_non_expert_is_forbidden(self):
        self.client.force_authenticate(self.member_user)

        response = self.client.get(self.list_url())

        self.assertEqual(response.status_code, 403)

    def test_staff_can_open_submissions_without_expert_role(self):
        self.client.force_authenticate(self.staff_user)

        response = self.client.get(self.list_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["counters"]["assigned"], 2)

    def test_manager_can_open_submissions_without_expert_role(self):
        self.client.force_authenticate(self.manager_user)

        response = self.client.get(self.list_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["counters"]["assigned"], 2)

    def test_distributed_evaluation_returns_only_assigned_submissions(self):
        self.program.is_distributed_evaluation = True
        self.program.save(update_fields=["is_distributed_evaluation"])
        ProjectExpertAssignment.objects.create(
            partner_program=self.program,
            project=self.project,
            expert=self.expert_user.expert,
        )
        ProjectExpertAssignment.objects.create(
            partner_program=self.program,
            project=self.other_project,
            expert=self.other_expert_user.expert,
        )
        self.client.force_authenticate(self.expert_user)

        response = self.client.get(self.list_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [self.link.id])
        self.assertEqual(response.data["counters"]["assigned"], 1)

    def test_manager_can_open_all_distributed_submissions_without_assignment(self):
        self.program.is_distributed_evaluation = True
        self.program.save(update_fields=["is_distributed_evaluation"])
        self.client.force_authenticate(self.manager_user)

        response = self.client.get(self.list_url())

        self.assertEqual(response.status_code, 200)
        returned_ids = {item["id"] for item in response.data["results"]}
        self.assertSetEqual(returned_ids, {self.link.id, self.other_link.id})
        self.assertEqual(response.data["counters"]["assigned"], 2)

    def test_distributed_evaluation_without_assignments_returns_empty_list(self):
        self.program.is_distributed_evaluation = True
        self.program.save(update_fields=["is_distributed_evaluation"])
        self.client.force_authenticate(self.expert_user)

        response = self.client.get(self.list_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])
        self.assertEqual(response.data["counters"]["assigned"], 0)

    def test_direct_url_to_unsubmitted_submission_is_not_available(self):
        self.client.force_authenticate(self.expert_user)

        response = self.client.get(self.detail_url(self.unsubmitted_link.id))

        self.assertEqual(response.status_code, 404)

    def test_draft_saves_scores_comment_and_numeric_total(self):
        self.client.force_authenticate(self.expert_user)

        response = self.client.put(
            self.draft_url(),
            {
                "comment": "Needs more details",
                "scores": [
                    {"criterion_id": self.criteria_impact.id, "value": 8},
                    {"criterion_id": self.criteria_quality.id, "value": 4},
                    {"criterion_id": self.criteria_comment.id, "value": "Good"},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        evaluation = ProjectEvaluation.objects.get(
            program_project=self.link,
            user=self.expert_user,
        )
        self.assertEqual(evaluation.status, ProjectEvaluation.STATUS_DRAFT)
        self.assertEqual(evaluation.comment, "Needs more details")
        self.assertEqual(evaluation.total_score, Decimal("8.00"))
        self.assertEqual(evaluation.evaluation_scores.count(), 3)

    def test_submit_finalizes_evaluation_and_locks_future_edits(self):
        self.client.force_authenticate(self.expert_user)

        response = self.client.post(
            self.submit_url(),
            {
                "comment": "Final comment",
                "scores": [
                    {"criterion_id": self.criteria_impact.id, "value": 9},
                    {"criterion_id": self.criteria_quality.id, "value": 4},
                    {"criterion_id": self.criteria_comment.id, "value": "Saved only"},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        evaluation = ProjectEvaluation.objects.get(
            program_project=self.link,
            user=self.expert_user,
        )
        self.assertEqual(evaluation.status, ProjectEvaluation.STATUS_SUBMITTED)
        self.assertIsNotNone(evaluation.submitted_at)
        self.assertEqual(evaluation.total_score, Decimal("8.50"))
        self.assertTrue(
            ProjectEvaluationScore.objects.filter(
                evaluation=evaluation,
                criterion=self.criteria_comment,
                value="Saved only",
            ).exists()
        )

        edit_response = self.client.put(
            self.draft_url(),
            {"comment": "Changed"},
            format="json",
        )
        self.assertEqual(edit_response.status_code, 400)

    def test_submit_requires_complete_valid_numeric_scores(self):
        self.client.force_authenticate(self.expert_user)

        response = self.client.post(
            self.submit_url(),
            {
                "scores": [
                    {"criterion_id": self.criteria_impact.id, "value": 7},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        evaluation = ProjectEvaluation.objects.get(
            program_project=self.link,
            user=self.expert_user,
        )
        self.assertEqual(evaluation.status, ProjectEvaluation.STATUS_DRAFT)
        self.assertIsNone(evaluation.submitted_at)
