from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from partner_programs.models import PartnerProgram
from project_rates.models import Criteria

User = get_user_model()


class CriteriaWeightTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.program = PartnerProgram.objects.create(
            name="Program",
            tag="program",
            description="Program description",
            city="Moscow",
            datetime_registration_ends=now + timezone.timedelta(days=2),
            datetime_started=now + timezone.timedelta(days=1),
            datetime_finished=now + timezone.timedelta(days=10),
        )

    def test_individual_criteria_can_be_saved_with_temporary_non_100_sum(self):
        Criteria.objects.create(
            partner_program=self.program,
            name="Impact",
            description="Impact",
            type="int",
            min_value=1,
            max_value=10,
            weight=40,
        )
        Criteria.objects.create(
            partner_program=self.program,
            name="Realism",
            description="Realism",
            type="int",
            min_value=1,
            max_value=10,
            weight=40,
        )

        total = (
            Criteria.objects.filter(partner_program=self.program)
            .filter(type__in=["int", "float"])
            .values_list("weight", flat=True)
        )
        self.assertEqual(sum(total), 80)

    def test_weight_must_be_from_1_to_100_on_criterion_validation(self):
        criterion = Criteria(
            partner_program=self.program,
            name="Invalid",
            description="Invalid",
            type="int",
            min_value=1,
            max_value=10,
            weight=0,
        )

        with self.assertRaises(ValidationError):
            criterion.full_clean()
