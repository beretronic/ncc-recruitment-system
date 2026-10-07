from datetime import timedelta
import io
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from recruitment.models import User, Applicant, Job, Application
from recruitment.authentication import issue_applicant_token


def make_pdf_bytes(text):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(50, 750, text)
    c.save()
    return buf.getvalue()


class HRCanCloseVacancy(TestCase):
    def test_hr_close_button_now_actually_closes_the_job(self):
        hr = User.objects.create_user(username="hr_close", password="Passw0rd!123", role="hr")
        job = Job.objects.create(title="Clerk", description="d", requirements="x",
                                  deadline="2027-01-31", posted_by=hr, status="open")
        client = APIClient()
        client.force_authenticate(user=hr)
        resp = client.patch(f"/api/jobs/{job.id}/", {"status": "closed"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        job.refresh_from_db()
        print(f"[CLOSE] Job status after HR clicks Close -> {job.status}")
        self.assertEqual(job.status, "closed")


class ExpiredJobsAutoClose(TestCase):
    def setUp(self):
        self.hr = User.objects.create_user(username="hr_exp", password="Passw0rd!123", role="hr")
        yesterday = (timezone.now().date() - timedelta(days=1)).isoformat()
        self.expired_job = Job.objects.create(
            title="Old Role", description="d", requirements="x",
            deadline=yesterday, posted_by=self.hr, status="open",  # still "open" in DB, deadline passed
        )

    def test_expired_job_flips_to_closed_when_listed(self):
        client = APIClient()
        resp = client.get("/api/jobs/")
        self.assertEqual(resp.status_code, 200)
        self.expired_job.refresh_from_db()
        print(f"[AUTO-CLOSE] Status after listing jobs (deadline was yesterday) -> {self.expired_job.status}")
        self.assertEqual(self.expired_job.status, "closed")
        self.assertNotIn(self.expired_job.id, [j["id"] for j in resp.data])

    def test_cannot_apply_to_expired_job_even_before_auto_close_runs(self):
        applicant = Applicant.objects.create(
            full_name="Late Applicant", email="late@example.com", password="x",
            is_verified=True, is_active=True,
        )
        tokens = issue_applicant_token(applicant)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        cv = io.BytesIO(make_pdf_bytes("Late Applicant CV"))
        cv.name = "cv.pdf"
        # Note: job.status is still "open" in the DB here, since no listing call has run yet.
        resp = client.post("/api/applications/", {"job": self.expired_job.id, "cv_file": cv}, format="multipart")
        print(f"[AUTO-CLOSE] Apply to expired-but-still-'open' job -> HTTP {resp.status_code}: {resp.data}")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Application.objects.count(), 0)
