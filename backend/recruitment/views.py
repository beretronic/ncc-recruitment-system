import logging
import secrets
import threading
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.mail import send_mail
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import User, Applicant, Job, Application, StatusAuditLog, Interview, JobDeletionRequest, ApplicationCV
from .serializers import (
    JobDeletionRequestSerializer,
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


logger = logging.getLogger(__name__)


def _send_email_safely(subject, message, recipient):
    """
    Send an email without letting SMTP problems break the request.

    Why this exists: Render's free tier blocks or throttles outbound SMTP, and
    Gmail can be slow. Sending inline meant a stalled connection made the whole
    request fail AFTER the database row had been saved (the user sees an error,
    retries, and is told "already applied"/"already registered"). So:
      * failures are caught and logged, never raised, and
      * in production (EMAIL_SEND_IN_BACKGROUND) the send happens in a
        background thread, so the HTTP response never waits on Gmail at all.
    """
    def _deliver():
        try:
            send_mail(subject=subject, message=message, from_email=None, recipient_list=[recipient])
            return True
        except Exception:
            logger.exception("Failed to send email to %s (subject: %s)", recipient, subject)
            return False

    if getattr(settings, "EMAIL_SEND_IN_BACKGROUND", False):
        threading.Thread(target=_deliver, daemon=True).start()
        return True  # queued; the outcome is only visible in the logs
    return _deliver()


class ApplicantRegisterView(generics.CreateAPIView):
    queryset = Applicant.objects.all()
    serializer_class = ApplicantRegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        applicant = serializer.save(verification_token=secrets.token_urlsafe(32))
        _send_email_safely(
            "Verify your NCC Recruitment account",
            f"Welcome {applicant.full_name}. Your verification token is: {applicant.verification_token}",
            applicant.email,
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


def _auto_close_expired_jobs():
    """
    There is no scheduled task runner (Celery/cron) in this deployment, so
    vacancies are closed "lazily": any job still marked open whose deadline
    has passed gets flipped to closed the next time jobs are read. Cheap
    (one UPDATE query) and keeps status accurate without needing a worker
    process running continuously in the background.
    """
    Job.objects.filter(status="open", deadline__lt=timezone.now().date()).update(status="closed")


class JobViewSet(viewsets.ModelViewSet):
    """
    HR/Admin: create, read, update.
    Delete: Admin only. HR must raise a deletion request instead (see
    request_deletion below), which an Admin approves or rejects.
    Everyone else -- anonymous visitors AND logged-in applicants -- can only
    list/retrieve OPEN jobs.
    """
    serializer_class = JobSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        if self.action == "destroy":
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated(), IsAdminOrHR()]

    def _requester_is_staff(self):
        user = self.request.user
        return bool(
            user and user.is_authenticated and getattr(user, "role", None) in ("admin", "hr")
        )

    def get_queryset(self):
        _auto_close_expired_jobs()
        qs = Job.objects.all().order_by("-created_at").prefetch_related("deletion_requests")
        # Previously this filter was skipped for ANY authenticated user, which
        # includes logged-in applicants -- so they saw closed vacancies. Only
        # staff (who need closed jobs to reopen/edit them) get the full list.
        if self.action in ("list", "retrieve") and not self._requester_is_staff():
            qs = qs.filter(status="open", deadline__gte=timezone.now().date())
        return qs

    def perform_create(self, serializer):
        serializer.save(posted_by=self.request.user)

    def perform_update(self, serializer):
        job = serializer.save(updated_by=self.request.user)
        # Reopening a vacancy whose deadline already passed would otherwise get
        # silently re-closed by _auto_close_expired_jobs() the next time jobs
        # are listed, making "Reopen" appear to do nothing. If HR explicitly
        # reopens an expired vacancy without also picking a new deadline,
        # extend it forward automatically (14 days) so the reopen actually sticks.
        if job.status == "open" and job.deadline < timezone.now().date():
            job.deadline = timezone.now().date() + timedelta(days=14)
            job.save(update_fields=["deadline"])

    def perform_destroy(self, instance):
        # An Admin deleting directly satisfies any request already waiting on
        # this vacancy -- close those out so they don't linger as "pending".
        instance.deletion_requests.filter(status="pending").update(
            status="approved", decided_by=self.request.user, decided_at=timezone.now()
        )
        instance.delete()

    @action(detail=True, methods=["post"], url_path="request-deletion")
    def request_deletion(self, request, pk=None):
        """HR asks for a vacancy to be deleted; nothing is deleted until an Admin approves."""
        job = self.get_object()
        if request.user.role == "admin":
            return Response(
                {"detail": "Admins can delete a vacancy directly; no request is needed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = (request.data.get("reason") or "").strip()
        if len(reason) < 5:
            return Response(
                {"reason": ["Please give a reason (at least 5 characters)."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if job.deletion_requests.filter(status="pending").exists():
            return Response(
                {"detail": "A deletion request for this vacancy is already awaiting Admin approval."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        req = JobDeletionRequest.objects.create(
            job=job, job_title=job.title, reason=reason, requested_by=request.user
        )
        return Response(JobDeletionRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class DeletionRequestListView(generics.ListAPIView):
    """Admin only. Pending requests by default; add ?status=all for the full history."""
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = JobDeletionRequestSerializer

    def get_queryset(self):
        qs = JobDeletionRequest.objects.select_related("requested_by", "decided_by", "job")
        if self.request.query_params.get("status") == "all":
            return qs.order_by("-requested_at")
        return qs.filter(status="pending").order_by("-requested_at")


class DeletionRequestDecisionView(APIView):
    """Admin only. Approve (deletes the vacancy) or reject (leaves it untouched)."""
    permission_classes = [IsAuthenticated, IsAdmin]
    decision = None  # set per-URL: "approve" | "reject"

    def post(self, request, pk):
        with transaction.atomic():
            req = get_object_or_404(JobDeletionRequest.objects.select_for_update(), pk=pk)
            if req.status != "pending":
                return Response(
                    {"detail": "This request has already been decided."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            approving = self.decision == "approve"
            req.status = "approved" if approving else "rejected"
            req.decided_by = request.user
            req.decided_at = timezone.now()
            req.save()
            if approving and req.job_id:
                req.job.delete()  # cascades to applications/interviews/audit rows; request row survives (SET_NULL)
        req.refresh_from_db()
        return Response(JobDeletionRequestSerializer(req).data)


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

        if job.status != "open" or job.deadline < timezone.now().date():
            return Response({"detail": "This vacancy is closed."}, status=status.HTTP_400_BAD_REQUEST)

        if Application.objects.filter(job=job, applicant=applicant).exists():
            return Response({"detail": "You have already applied for this vacancy."}, status=status.HTTP_400_BAD_REQUEST)

        existing_applicants = Application.objects.filter(job=job).exclude(applicant=applicant).select_related("applicant")
        for existing in existing_applicants:
            if is_duplicate_applicant(applicant.full_name, applicant.email, existing.applicant.full_name, existing.applicant.email):
                return Response({"detail": "A very similar application already exists for this vacancy."}, status=status.HTTP_400_BAD_REQUEST)

        cv_text = extract_text_from_pdf(cv_file)
        fit_score = compute_fit_score(cv_text, job.requirements)
        cv_file.seek(0)
        cv_bytes = cv_file.read()
        cv_file.seek(0)

        try:
            # One transaction: the application, its stored CV and its audit entry
            # all exist, or none do. A failure can never leave a half-created
            # application that then blocks a retry with "already applied".
            with transaction.atomic():
                application = Application.objects.create(
                    job=job, applicant=applicant, cv_file=cv_file,
                    cv_text=cv_text, fit_score=fit_score, status="Applied",
                )
                ApplicationCV.objects.create(application=application, data=cv_bytes)
                StatusAuditLog.objects.create(
                    application=application, old_status="", new_status="Applied", changed_by=None,
                )
        except IntegrityError:
            return Response({"detail": "You have already applied for this vacancy."}, status=status.HTTP_400_BAD_REQUEST)

        _send_email_safely(
            f"Application received: {job.title}",
            f"Hi {applicant.full_name}, your application for {job.title} has been received.",
            applicant.email,
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


class ApplicationCVView(APIView):
    """
    Serves an application's CV PDF. Allowed for HR/Admin, and for the applicant
    who owns the application -- nobody else. The frontend fetches this with the
    login token and shows it from a blob URL, so CVs are never exposed at a
    public, guessable address and the browser's iframe/X-Frame-Options rules
    don't get in the way.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        application = get_object_or_404(Application, pk=pk)
        user = request.user
        is_staff = getattr(user, "role", None) in ("admin", "hr")
        is_owner = bool(getattr(user, "is_applicant", False)) and application.applicant_id == user.id
        if not (is_staff or is_owner):
            return Response({"detail": "You do not have permission to view this CV."},
                            status=status.HTTP_403_FORBIDDEN)

        data = None
        stored = ApplicationCV.objects.filter(application=application).values_list("data", flat=True).first()
        if stored:
            data = bytes(stored)
        else:
            # CVs uploaded before database storage existed: use the old on-disk
            # copy if it somehow survived; otherwise it is gone.
            try:
                with application.cv_file.open("rb") as f:
                    data = f.read()
            except (FileNotFoundError, ValueError, OSError):
                data = None

        if not data:
            return Response({"detail": "This CV file is no longer available."},
                            status=status.HTTP_404_NOT_FOUND)
        response = HttpResponse(data, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="cv-{application.id}.pdf"'
        return response


def _format_interview_time(dt):
    return timezone.localtime(dt).strftime("%A, %d %B %Y at %H:%M")


def _notify_interview_scheduled(application, interview):
    """
    Email the applicant their interview date/time. Used when HR explicitly
    schedules an interview for an application that is ALREADY at "Interview"
    (e.g. after "Move to Interview" auto-scheduled one) -- in that case there is
    no status change, so the normal status-update email never fires.
    """
    rescheduled = application.interviews.exclude(pk=interview.pk).exists()
    verb = "has been rescheduled to" if rescheduled else "is scheduled for"
    _send_email_safely(
        f"Interview {'rescheduled' if rescheduled else 'scheduled'}: {application.job.title}",
        (
            f"Hi {application.applicant.full_name}, your interview for "
            f"{application.job.title} {verb} {_format_interview_time(interview.date_time)}. "
            f"Please let us know if this time does not work for you."
        ),
        application.applicant.email,
    )


def _apply_status_change(application, new_status, changed_by):
    """Shared helper: updates status, writes audit log, emails the applicant (objectives 2, 4, 5).

    When the new status is "Interview", this also makes sure an Interview record
    exists for the application. If HR scheduled one explicitly (via the
    InterviewViewSet, with a chosen date/time) that one is used as-is. Otherwise
    one is auto-scheduled for 08:00, 7 days from now (in the server's configured
    local time zone), and that date is included in the notification email.
    """
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

    interview_line = ""
    if new_status == "Interview":
        interview = application.interviews.order_by("-id").first()
        if interview is None:
            scheduled = timezone.localtime(timezone.now()) + timedelta(days=7)
            scheduled = scheduled.replace(hour=8, minute=0, second=0, microsecond=0)
            interview = Interview.objects.create(application=application, date_time=scheduled)
        interview_line = (
            f"\n\nYour interview has been scheduled for "
            f"{_format_interview_time(interview.date_time)}. "
            f"Please let us know if this time does not work for you."
        )

    _send_email_safely(
        f"Application status update: {application.job.title}",
        (
            f"Hi {application.applicant.full_name}, your application for "
            f"{application.job.title} has changed from {old_status} to {new_status}."
            f"{interview_line}"
        ),
        application.applicant.email,
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
        application = interview.application
        if application.status != "Interview":
            # Moves the application to Interview, logs it, and emails the new
            # status together with this interview's date.
            _apply_status_change(application, "Interview", self.request.user)
        else:
            # Already at Interview: no status change, so the status email would
            # never fire -- send the interview details directly instead.
            _notify_interview_scheduled(application, interview)


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
