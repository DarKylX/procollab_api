from django.urls import path

from moderation.views import (
    ModerationDecisionView,
    ModerationLogListView,
    ModerationProgramArchiveView,
    ModerationProgramDetailView,
    ModerationProgramFreezeView,
    ModerationProgramListView,
    ModerationProgramRestoreView,
    ModerationVerificationDecisionView,
    ModerationVerificationRequestDetailView,
    ModerationVerificationRequestListView,
    ModerationVerificationRevokeView,
    RejectionReasonListView,
    VerificationRejectionReasonListView,
)

app_name = "moderation"

urlpatterns = [
    path("programs/", ModerationProgramListView.as_view(), name="program-list"),
    path(
        "programs/<int:pk>/",
        ModerationProgramDetailView.as_view(),
        name="program-detail",
    ),
    path(
        "programs/<int:pk>/decision/",
        ModerationDecisionView.as_view(),
        name="program-decision",
    ),
    path(
        "programs/<int:pk>/freeze/",
        ModerationProgramFreezeView.as_view(),
        name="program-freeze",
    ),
    path(
        "programs/<int:pk>/restore/",
        ModerationProgramRestoreView.as_view(),
        name="program-restore",
    ),
    path(
        "programs/<int:pk>/archive/",
        ModerationProgramArchiveView.as_view(),
        name="program-archive",
    ),
    path("logs/", ModerationLogListView.as_view(), name="log-list"),
    path("rejection-reasons/", RejectionReasonListView.as_view(), name="reasons"),
    path(
        "verification/rejection-reasons/",
        VerificationRejectionReasonListView.as_view(),
        name="verification-reasons",
    ),
    path(
        "verification/",
        ModerationVerificationRequestListView.as_view(),
        name="verification-list",
    ),
    path(
        "verification/<int:pk>/",
        ModerationVerificationRequestDetailView.as_view(),
        name="verification-detail",
    ),
    path(
        "verification/<int:pk>/decision/",
        ModerationVerificationDecisionView.as_view(),
        name="verification-decision",
    ),
    path(
        "verification-requests/",
        ModerationVerificationRequestListView.as_view(),
        name="verification-request-list",
    ),
    path(
        "verification-requests/<int:pk>/",
        ModerationVerificationRequestDetailView.as_view(),
        name="verification-request-detail",
    ),
    path(
        "verification-requests/<int:pk>/decision/",
        ModerationVerificationDecisionView.as_view(),
        name="verification-request-decision",
    ),
    path(
        "programs/<int:pk>/verification/revoke/",
        ModerationVerificationRevokeView.as_view(),
        name="program-verification-revoke",
    ),
]
