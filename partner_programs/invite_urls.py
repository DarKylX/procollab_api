from django.urls import path

from partner_programs.views import (
    PartnerProgramInviteDeleteView,
    PartnerProgramInviteListCreateView,
    PartnerProgramInviteResendView,
    PartnerProgramInviteRevokeView,
    PublicPartnerProgramInviteAcceptView,
    PublicPartnerProgramInviteView,
)

app_name = "partner_program_invites"

program_invite_patterns = [
    path(
        "<int:pk>/invites/",
        PartnerProgramInviteListCreateView.as_view(),
        name="program-invites",
    ),
    path(
        "<int:pk>/invites/<int:invite_id>/revoke/",
        PartnerProgramInviteRevokeView.as_view(),
        name="program-invite-revoke",
    ),
    path(
        "<int:pk>/invites/<int:invite_id>/",
        PartnerProgramInviteDeleteView.as_view(),
        name="program-invite-delete",
    ),
    path(
        "<int:pk>/invites/<int:invite_id>/resend/",
        PartnerProgramInviteResendView.as_view(),
        name="program-invite-resend",
    ),
]

public_invite_patterns = [
    path(
        "<str:token>/",
        PublicPartnerProgramInviteView.as_view(),
        name="public-invite-detail",
    ),
    path(
        "<str:token>/accept/",
        PublicPartnerProgramInviteAcceptView.as_view(),
        name="public-invite-accept",
    ),
]
