from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ApplicantRegisterView, ApplicantVerifyView, ApplicantLoginView, ApplicantMeView,
    JobViewSet, ApplicationSubmitView, MyApplicationsView, JobApplicationsView,
    ApplicationStatusUpdateView, BulkStatusUpdateView, ApplicationAuditLogView,
    InterviewViewSet, JobRecommendationsView, DashboardSummaryView, JobLeaderboardView,
    StaffMeView, StaffListCreateView, StaffDetailView,
    ApplicantAdminListView, ApplicantAdminDetailView, AdminSummaryView,
    ApplicationDetailView,
)

router = DefaultRouter()
router.register("jobs", JobViewSet, basename="job")
router.register("interviews", InterviewViewSet, basename="interview")

urlpatterns = [
    path("applicants/register/", ApplicantRegisterView.as_view(), name="applicant-register"),
    path("applicants/verify/", ApplicantVerifyView.as_view(), name="applicant-verify"),
    path("applicants/login/", ApplicantLoginView.as_view(), name="applicant-login"),
    path("applicants/me/", ApplicantMeView.as_view(), name="applicant-me"),

    path("applications/", ApplicationSubmitView.as_view(), name="application-submit"),
    path("applications/mine/", MyApplicationsView.as_view(), name="my-applications"),
    path("applications/bulk-status/", BulkStatusUpdateView.as_view(), name="application-bulk-status"),
    path("applications/<int:application_id>/status/", ApplicationStatusUpdateView.as_view(), name="application-status"),
    path("applications/<int:application_id>/audit-log/", ApplicationAuditLogView.as_view(), name="application-audit-log"),
    path("applications/<int:pk>/", ApplicationDetailView.as_view(), name="application-detail"),

    path("jobs/<int:job_id>/applications/", JobApplicationsView.as_view(), name="job-applications"),
    path("jobs/<int:job_id>/leaderboard/", JobLeaderboardView.as_view(), name="job-leaderboard"),

    path("recommendations/", JobRecommendationsView.as_view(), name="job-recommendations"),
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),

    # ---- Staff (HR/Admin) account management - Admin only ----
    path("staff/me/", StaffMeView.as_view(), name="staff-me"),
    path("staff/", StaffListCreateView.as_view(), name="staff-list-create"),
    path("staff/<int:staff_id>/", StaffDetailView.as_view(), name="staff-detail"),

    # ---- Applicant account management - Admin only ----
    path("admin/applicants/", ApplicantAdminListView.as_view(), name="admin-applicant-list"),
    path("admin/applicants/<int:applicant_id>/", ApplicantAdminDetailView.as_view(), name="admin-applicant-detail"),
    path("admin/summary/", AdminSummaryView.as_view(), name="admin-summary"),

    path("", include(router.urls)),
]
