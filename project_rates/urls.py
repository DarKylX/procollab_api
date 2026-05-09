from django.urls import path

from project_rates.views import (
    ExpertEvaluationProgramListView,
    ProjectEvaluationDraftView,
    ProjectEvaluationSubmitView,
    ProjectListForRate,
    ProjectSubmissionDetailView,
    ProjectSubmissionListView,
    RateProject,
)

urlpatterns = [
    path(
        "expert/evaluations/",
        ExpertEvaluationProgramListView.as_view(),
        name="expert-evaluation-programs",
    ),
    path(
        "<int:program_id>/submissions/",
        ProjectSubmissionListView.as_view(),
        name="project-evaluation-submissions",
    ),
    path(
        "<int:program_id>/submissions/<int:program_project_id>/",
        ProjectSubmissionDetailView.as_view(),
        name="project-evaluation-submission-detail",
    ),
    path(
        "<int:program_id>/submissions/<int:program_project_id>/draft/",
        ProjectEvaluationDraftView.as_view(),
        name="project-evaluation-draft",
    ),
    path(
        "<int:program_id>/submissions/<int:program_project_id>/submit/",
        ProjectEvaluationSubmitView.as_view(),
        name="project-evaluation-submit",
    ),
    path("rate/<int:project_id>", RateProject.as_view()),
    path("<int:program_id>", ProjectListForRate.as_view()),
]
