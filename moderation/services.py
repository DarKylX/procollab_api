from django.db import transaction

from moderation.models import ModerationLog
from notifications.services import notify_program_submitted_to_moderation
from partner_programs.models import PartnerProgram


class ModerationTransitionError(Exception):
    def __init__(self, current_status: str):
        self.current_status = current_status
        super().__init__(current_status)


def create_moderation_log(
    *,
    program: PartnerProgram,
    author=None,
    action: str,
    status_before: str,
    status_after: str,
    comment: str = "",
    rejection_reason: str = "",
    sections_to_fix: list[str] | None = None,
) -> ModerationLog:
    return ModerationLog.objects.create(
        program=program,
        author=author if getattr(author, "is_authenticated", False) else None,
        action=action,
        status_before=status_before or "",
        status_after=status_after or "",
        comment=comment or "",
        rejection_reason=rejection_reason or "",
        sections_to_fix=sections_to_fix or [],
    )


@transaction.atomic
def submit_program_to_moderation(
    program: PartnerProgram,
    *,
    author=None,
    comment: str = "",
) -> ModerationLog:
    status_before = program.status
    program.status = PartnerProgram.STATUS_PENDING_MODERATION
    program.save(update_fields=["status", "datetime_updated"])
    log = create_moderation_log(
        program=program,
        author=author,
        action=ModerationLog.ACTION_SUBMITTED,
        status_before=status_before,
        status_after=program.status,
        comment=comment,
    )
    notify_program_submitted_to_moderation(program, log)
    return log


@transaction.atomic
def withdraw_program_from_moderation(
    program: PartnerProgram,
    *,
    author,
    comment: str = "",
) -> ModerationLog:
    if program.status != PartnerProgram.STATUS_PENDING_MODERATION:
        raise ModerationTransitionError(program.status)

    status_before = program.status
    program.status = PartnerProgram.STATUS_DRAFT
    program.save(update_fields=["status", "datetime_updated"])
    return create_moderation_log(
        program=program,
        author=author,
        action=ModerationLog.ACTION_WITHDRAWN,
        status_before=status_before,
        status_after=program.status,
        comment=comment,
    )
