import secrets
from django.contrib.auth.hashers import check_password
from django.core.mail import send_mail
from django.utils import timezone
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import User, Applicant, Job, Application, StatusAuditLog, Interview
from .serializers import (
    ApplicantRegisterSerializer, ApplicantSerializer, JobSerializer,
    ApplicationCreateSerializer, ApplicationSerializer,
    StatusUpdateSerializer, BulkStatusUpdateSerializer,
    StatusAuditLogSerializer, InterviewSerializer,
    JobRecommendationSerializer, LeaderboardEntrySerializer,
    StaffSerializer, StaffCreateSerializer, StaffUpdateSerializer,
    ApplicantAdminSerializer, ApplicantAdminUpdateSerializer,
)
from .authentication import issue_applicant_token, ApplicantJWTAuthentication
from .permissions import IsAdminOrHR, IsApplicant, IsAdmin
from .matching import extract_text_from_pdf, compute_fit_score, is_duplicate_applicant
from .dashboard import get_dashboard_summary, get_top_candidates


class ApplicantRegisterView(generics.CreateAPIView):
    queryset = Applicant.objects.all()
    serializer_class = ApplicantRegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        applicant = serializer.save(verification_token=secrets.token_urlsafe(32))
        send_mail(
            subject="Verify your NCC Recruitment account",
            message=f"Welcome {applicant.full_name}. Your verification token is: {applicant.verification_token}",
            from_email=None,
            recipient_list=[applicant.email],
        )


class ApplicantVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")
        try:
            applicant = Applicant.objects.get(verification_token=token)
        except Applicant.DoesNotExist:
            return Response({"detail": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        applicant.is_verified = True
        applicant.verification_token = ""
        applicant.save()
        return Response({"detail": "Account verified. You may now log in."})


class ApplicantLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        try:
            applicant = Applicant.objects.get(email=email)
        except Applicant.DoesNotExist:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        if not check_password(password, applicant.password):
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        if not applicant.is_verified:
            return Response({"detail": "Account not verified. Check your email."}, status=status.HTTP_403_FORBIDDEN)

        if not applicant.is_active:
            return Response({"detail": "This account has been suspended. Contact the administrator."}, status=status.HTTP_403_FORBIDDEN)

        tokens = issue_applicant_token(applicant)
        return Response(tokens)


class ApplicantMeView(APIView):
    authentication_classes = [ApplicantJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ApplicantSerializer(request.user)
        return Response(serializer.data)


class JobViewSet(viewsets.ModelViewSet):
    """
    HR/Admin: full CRUD.
    Anyone (including anonymous applicants): can list/retrieve OPEN jobs only.
    """
    serializer_class = JobSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        if self.action == "destroy":
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated(), IsAdminOrHR()]

    def get_queryset(self):
        qs = Job.objects.all().order_by("-created_at")
        if self.action in ("list", "retrieve") and not (
            self.request.user and self.request.user.is_authenticated
        ):
            qs = qs.filter(status="open", deadline__gte=timezone.now().date())
        return qs

    def perform_create(self, serializer):
        serializer.save(posted_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class ApplicationSubmitView(APIView):
    """Applicant submits a CV for a job. Runs duplicate detection + TF-IDF fit scoring."""
    authentication_classes = [ApplicantJWTAuthentication]
    permission_classes = [IsAuthenticated, IsApplicant]

    def post(self, request):
        serializer = ApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job = serializer.validated_data["job"]
        cv_file = serializer.validated_data["cv_file"]
        applicant = request.user

        if job.status != "open":
            return Response({"detail": "This vacancy is closed."}, status=status.HTTP_400_BAD_REQUEST)

        if Application.objects.filter(job=job, applicant=applicant).exists():
            return Response({"detail": "You have already applied for this vacancy."}, status=status.HTTP_400_BAD_REQUEST)

        existing_applicants = Application.objects.filter(job=job).exclude(applicant=applicant).select_related("applicant")
        for existing in existing_applicants:
            if is_duplicate_applicant(applicant.full_name, applicant.email, existing.applicant.full_name, existing.applicant.email):
                return Response({"detail": "A very similar application already exists for this vacancy."}, status=status.HTTP_400_BAD_REQUEST)

        cv_text = extract_text_from_pdf(cv_file)
        fit_score = compute_fit_score(cv_text, job.requirements)

        try:
            application = Application.objects.create(
                job=job, applicant=applicant, cv_file=cv_file,
                cv_text=cv_text, fit_score=fit_score, status="Applied",
            )
        except IntegrityError:
            return Response({"detail": "You have already applied for this vacancy."}, status=status.HTTP_400_BAD_REQUEST)

        StatusAuditLog.objects.create(
            application=application, old_status="", new_status="Applied", changed_by=None,
        )

        send_mail(
            subject=f"Application received: {job.title}",
            message=f"Hi {applicant.full_name}, your application for {job.title} has been received.",
            from_email=None,
            recipient_list=[applicant.email],
        )

        return Response(ApplicationSerializer(application).data, status=status.HTTP_201_CREATED)


class MyApplicationsView(generics.ListAPIView):
    """Applicant view of their own applications (status tracking - objective 2)."""
    authentication_classes = [ApplicantJWTAuthentication]
    permission_classes = [IsAuthenticated, IsApplicant]
    serializer_class = ApplicationSerializer

    def get_queryset(self):
        return Application.objects.filter(applicant=self.request.user).order_by("-applied_at")


class JobApplicationsView(generics.ListAPIView):
    """HR/Admin view of applicants for a given job, ranked by fit_score (objective 3)."""
    permission_classes = [IsAuthenticated, IsAdminOrHR]
    serializer_class = ApplicationSerializer

    def get_queryset(self):
        job_id = self.kwargs["job_id"]
        return Application.objects.filter(job_id=job_id).order_by("-fit_score")


class ApplicationDetailView(generics.RetrieveAPIView):
    """
    HR/Admin: fetch a single application by ID, regardless of which job it's
    for. Used so things like the global leaderboard (not scoped to one job)
    can open the same CV review modal as the per-job applicant list.
    """
    permission_classes = [IsAuthenticated, IsAdminOrHR]
    serializer_class = ApplicationSerializer
    queryset = Application.objects.all()


def _apply_status_change(application, new_status, changed_by):
    """Shared helper: updates status, writes audit log, emails the applicant (objectives 2, 4, 5)."""
    old_status = application.status
    if old_status == new_status:
        return application

    application.status = new_status
    application.save(update_fields=["status", "updated_at"])

    StatusAuditLog.objects.create(
        application=application,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
    )

    send_mail(
        subject=f"Application status update: {application.job.title}",
        message=(
            f"Hi {application.applicant.full_name}, your application for "
            f"{application.job.title} has changed from {old_status} to {new_status}."
        ),
        from_email=None,
        recipient_list=[application.applicant.email],
    )
    return application


class ApplicationStatusUpdateView(APIView):
    """HR/Admin updates a single application's status."""
    permission_classes = [IsAuthenticated, IsAdminOrHR]

    def patch(self, request, application_id):
        application = get_object_or_404(Application, id=application_id)
        serializer = StatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application = _apply_status_change(
            application, serializer.validated_data["status"], request.user
        )
        return Response(ApplicationSerializer(application).data)


class BulkStatusUpdateView(APIView):
    """HR/Admin updates status for multiple applications at once (SRS: ATS bulk actions)."""
    permission_classes = [IsAuthenticated, IsAdminOrHR]

    def post(self, request):
        serializer = BulkStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ids = serializer.validated_data["application_ids"]
        new_status = serializer.validated_data["status"]

        applications = Application.objects.filter(id__in=ids)
        updated = []
        for application in applications:
            updated.append(_apply_status_change(application, new_status, request.user))

        return Response(ApplicationSerializer(updated, many=True).data)


class ApplicationAuditLogView(generics.ListAPIView):
    """Full status history for one application (objective 5 - audit trail)."""
    permission_classes = [IsAuthenticated, IsAdminOrHR]
    serializer_class = StatusAuditLogSerializer

    def get_queryset(self):
        application_id = self.kwargs["application_id"]
        return StatusAuditLog.objects.filter(application_id=application_id).order_by("timestamp")


class InterviewViewSet(viewsets.ModelViewSet):
    """HR/Admin schedules and manages interviews for applications."""
    serializer_class = InterviewSerializer
    permission_classes = [IsAuthenticated, IsAdminOrHR]

    def get_queryset(self):
        qs = Interview.objects.all().order_by("date_time")
        application_id = self.request.query_params.get("application")
        if application_id:
            qs = qs.filter(application_id=application_id)
        return qs

    def perform_create(self, serializer):
        interview = serializer.save()
        _apply_status_change(interview.application, "Interview", self.request.user)


class JobRecommendationsView(APIView):
    """
    Applicant's personalised job recommendations: TF-IDF match between their
    most recent CV on file and every currently open job (SRS: recommendations).
    """
    authentication_classes = [ApplicantJWTAuthentication]
    permission_classes = [IsAuthenticated, IsApplicant]

    def get(self, request):
        applicant = request.user

        latest_application = (
            Application.objects.filter(applicant=applicant)
            .exclude(cv_text="")
            .order_by("-applied_at")
            .first()
        )
        if not latest_application:
            return Response(
                {"detail": "Apply to at least one job first so we have a CV on file to match against."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        already_applied_job_ids = set(
            Application.objects.filter(applicant=applicant).values_list("job_id", flat=True)
        )

        open_jobs = Job.objects.filter(
            status="open", deadline__gte=timezone.now().date()
        ).exclude(id__in=already_applied_job_ids)

        recommendations = []
        for job in open_jobs:
            score = compute_fit_score(latest_application.cv_text, job.requirements)
            recommendations.append({"job": job, "match_score": score})

        recommendations.sort(key=lambda r: r["match_score"], reverse=True)
        top = recommendations[:10]

        serializer = JobRecommendationSerializer(top, many=True)
        return Response(serializer.data)


class DashboardSummaryView(APIView):
    """
    HR/Admin analytics dashboard: applicant counts, applicants-per-job,
    status funnel conversion, average time-to-hire, and a global top-candidate
    leaderboard (SRS: dashboard/analytics).
    """
    permission_classes = [IsAuthenticated, IsAdminOrHR]

    def get(self, request):
        return Response(get_dashboard_summary())


class JobLeaderboardView(APIView):
    """Top-candidate leaderboard for one specific job (SRS: per-job leaderboard)."""
    permission_classes = [IsAuthenticated, IsAdminOrHR]

    def get(self, request, job_id):
        limit = int(request.query_params.get("limit", 10))
        entries = get_top_candidates(job_id=job_id, limit=limit)
        serializer = LeaderboardEntrySerializer(entries, many=True)
        return Response(serializer.data)


class StaffMeView(APIView):
    """
    Lets a logged-in HR/Admin find out their own role, so the frontend can
    show the correct dashboard (Admin vs HR) and hide/show controls accordingly.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(StaffSerializer(request.user).data)


class StaffListCreateView(generics.ListCreateAPIView):
    """
    Admin-only. Lists all HR/Admin accounts, and creates new ones.
    This replaces having to use Django admin to add HR staff.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = User.objects.all().order_by("-date_joined")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return StaffCreateSerializer
        return StaffSerializer


class StaffDetailView(APIView):
    """
    Admin-only. Activate/deactivate a staff account (soft delete - preserves
    all historical audit records, e.g. jobs they posted, statuses they
    changed), or change their role.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, staff_id):
        user = get_object_or_404(User, id=staff_id)
        serializer = StaffUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if "is_active" in serializer.validated_data:
            if user.id == request.user.id and not serializer.validated_data["is_active"]:
                return Response(
                    {"detail": "You cannot deactivate your own account."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.is_active = serializer.validated_data["is_active"]

        if "role" in serializer.validated_data:
            user.role = serializer.validated_data["role"]

        user.save()
        return Response(StaffSerializer(user).data)


class ApplicantAdminListView(APIView):
    """Admin-only. Lists all applicant accounts, with application counts, for account management."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        applicants = Applicant.objects.all().order_by("-created_at")
        data = []
        for a in applicants:
            data.append({
                "id": a.id,
                "full_name": a.full_name,
                "email": a.email,
                "phone": a.phone,
                "is_verified": a.is_verified,
                "is_active": a.is_active,
                "created_at": a.created_at,
                "application_count": a.applications.count(),
            })
        serializer = ApplicantAdminSerializer(data, many=True)
        return Response(serializer.data)


class ApplicantAdminDetailView(APIView):
    """Admin-only. Suspend/reactivate an applicant account, or force-verify one."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, applicant_id):
        applicant = get_object_or_404(Applicant, id=applicant_id)
        serializer = ApplicantAdminUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if "is_active" in serializer.validated_data:
            applicant.is_active = serializer.validated_data["is_active"]

        if "is_verified" in serializer.validated_data:
            applicant.is_verified = serializer.validated_data["is_verified"]
            if applicant.is_verified:
                applicant.verification_token = ""  # invalidate any outstanding token

        applicant.save()
        return Response({
            "detail": "Updated.",
            "is_active": applicant.is_active,
            "is_verified": applicant.is_verified,
        })


class AdminSummaryView(APIView):
    """
    Admin-only, deliberately lighter-weight than the HR analytics dashboard:
    account/vacancy counts only, no matching-score detail.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        return Response({
            "total_vacancies_open": Job.objects.filter(status="open").count(),
            "total_vacancies_closed": Job.objects.filter(status="closed").count(),
            "total_applicants": Applicant.objects.count(),
            "total_applicants_pending_verification": Applicant.objects.filter(is_verified=False).count(),
            "total_hr_staff": User.objects.filter(role="hr").count(),
            "total_applications": Application.objects.count(),
        })
