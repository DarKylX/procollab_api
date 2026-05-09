from django.urls import path

from moderation.views import (
    ModerationLogListView,
    ModerationVerificationDecisionView,
    ModerationVerificationRequestDetailView,
    ModerationVerificationRequestListView,
    ModerationVerificationRevokeView,
    VerificationRejectionReasonListView,
)

app_name = "moderation"

urlpatterns = [
    path("logs/", ModerationLogListView.as_view(), name="log-list"),
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
