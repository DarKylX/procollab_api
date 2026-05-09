from moderation.models import ModerationLog
from partner_programs.models import PartnerProgram


def create_moderation_log(
    *,
    program: PartnerProgram,
    author=None,
    action: str,
    status_before: str,
    status_after: str,
    comment: str = "",
    rejection_reason: str = "",
) -> ModerationLog:
    return ModerationLog.objects.create(
        program=program,
        author=author if getattr(author, "is_authenticated", False) else None,
        action=action,
        status_before=status_before or "",
        status_after=status_after or "",
        comment=comment or "",
        rejection_reason=rejection_reason or "",
    )
