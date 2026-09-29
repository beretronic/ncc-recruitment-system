"""
Validation / edge-case tests for Chapter 5.3.3 (Validation) and 5.3.1 additional evidence.

Run with:
DJANGO_SETTINGS_MODULE=ncc_recruitment.test_settings python manage.py test recruitment.tests_validation -v 2
"""
import io
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status as http_status

from recruitment.models import User, Applicant, Job, Application
from recruitment.authentication import issue_applicant_token


def make_pdf_bytes(text: str) -> bytes:
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    t = c.beginText(50, 750)
    for line in text.split("\n"):
        t.textLine(line)
    c.drawText(t)
    c.save()
    return buf.getvalue()


class RegistrationValidation(TestCase):
    """System rejects malformed applicant registration data (5.3.3 Validation)."""

    def test_invalid_email_format_rejected(self):
        client = APIClient()
        resp = client.post("/api/applicants/register/", {
            "full_name": "Test Person",
            "email": "not-an-email",
            "password": "SomePass123",
        }, format="json")
        print(f"[VALIDATION] Invalid email -> HTTP {resp.status_code}: {resp.data}")
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", resp.data)

    def test_password_below_minimum_length_rejected(self):
        client = APIClient()
        resp = client.post("/api/applicants/register/", {
            "full_name": "Test Person",
            "email": "valid@example.com",
            "password": "short",
        }, format="json")
        print(f"[VALIDATION] Short password -> HTTP {resp.status_code}: {resp.data}")
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", resp.data)

    def test_duplicate_email_rejected(self):
        Applicant.objects.create(full_name="Existing", email="dupe@example.com", password="x")
        client = APIClient()
        resp = client.post("/api/applicants/register/", {
            "full_name": "Another Person",
            "email": "dupe@example.com",
            "password": "SomePass123",
        }, format="json")
        print(f"[VALIDATION] Duplicate email -> HTTP {resp.status_code}: {resp.data}")
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)


class ApplicationValidation(TestCase):
    """System rejects invalid application submissions (5.3.3 Validation)."""

    def setUp(self):
        self.hr = User.objects.create_user(username="hr_val", password="Passw0rd!123", role="hr")
        self.applicant = Applicant.objects.create(
            full_name="Grace Ncube", email="grace@example.com", password="x", is_verified=True, is_active=True,
        )
        self.job = Job.objects.create(
            title="Finance Officer", description="d", requirements="finance, budgeting",
            deadline="2027-01-31", posted_by=self.hr,
        )
        tokens = issue_applicant_token(self.applicant)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    def test_non_pdf_cv_rejected(self):
        fake_file = io.BytesIO(b"not really a pdf")
        fake_file.name = "cv.docx"
        resp = self.client.post("/api/applications/", {"job": self.job.id, "cv_file": fake_file}, format="multipart")
        print(f"[VALIDATION] Non-PDF upload -> HTTP {resp.status_code}: {resp.content}")
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_duplicate_application_rejected(self):
        cv = io.BytesIO(make_pdf_bytes("Grace Ncube\nFinance and budgeting experience."))
        cv.name = "grace_cv.pdf"
        first = self.client.post("/api/applications/", {"job": self.job.id, "cv_file": cv}, format="multipart")
        self.assertEqual(first.status_code, http_status.HTTP_201_CREATED)

        cv2 = io.BytesIO(make_pdf_bytes("Grace Ncube\nFinance and budgeting experience."))
        cv2.name = "grace_cv2.pdf"
        second = self.client.post("/api/applications/", {"job": self.job.id, "cv_file": cv2}, format="multipart")
        print(f"[VALIDATION] Duplicate application -> HTTP {second.status_code}: {second.data}")
        self.assertEqual(second.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Application.objects.filter(job=self.job, applicant=self.applicant).count(), 1)

    def test_application_to_closed_job_rejected(self):
        self.job.status = "closed"
        self.job.save()
        cv = io.BytesIO(make_pdf_bytes("Grace Ncube CV"))
        cv.name = "grace_cv.pdf"
        resp = self.client.post("/api/applications/", {"job": self.job.id, "cv_file": cv}, format="multipart")
        print(f"[VALIDATION] Application to closed job -> HTTP {resp.status_code}: {resp.data}")
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn("closed", resp.data["detail"].lower())

    def test_fuzzy_duplicate_applicant_detected(self):
        """A near-identical applicant (typo'd name, same email pattern) is blocked (rapidfuzz)."""
        near_dupe = Applicant.objects.create(
            full_name="Grace Ncub", email="grace1@example.com", password="x", is_verified=True, is_active=True,
        )
        Application.objects.create(
            job=self.job, applicant=near_dupe, cv_file="cvs/x.pdf",
            cv_text="finance", fit_score=40.0, status="Applied",
        )
        cv = io.BytesIO(make_pdf_bytes("Grace Ncube CV"))
        cv.name = "grace_cv.pdf"
        resp = self.client.post("/api/applications/", {"job": self.job.id, "cv_file": cv}, format="multipart")
        print(f"[VALIDATION] Fuzzy near-duplicate applicant -> HTTP {resp.status_code}: {resp.data}")
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
