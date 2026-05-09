import logging

from django.utils import timezone

from moderation.services import freeze_program_automatically
from partner_programs.models import PartnerProgram
from procollab.celery import app

logger = logging.getLogger(__name__)


@app.task(name="moderation.tasks.freeze_stale_programs")
def freeze_stale_programs() -> dict:
    now = timezone.now()
    frozen_ids: list[int] = []
    errors: list[dict] = []

    programs = PartnerProgram.objects.filter(
        status=PartnerProgram.STATUS_PUBLISHED,
    ).prefetch_related("materials", "managers")

    for program in programs:
        try:
            log = freeze_program_automatically(program, now=now)
            if log is not None:
                frozen_ids.append(program.id)
        except Exception as exc:
            logger.exception("Auto-freeze failed for program %s", program.id)
            errors.append({"program_id": program.id, "error": str(exc)})

    return {
        "frozen_count": len(frozen_ids),
        "frozen_ids": frozen_ids,
        "errors": errors,
    }
