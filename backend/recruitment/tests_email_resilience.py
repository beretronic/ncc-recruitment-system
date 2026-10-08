from unittest import mock
from django.test import TestCase
from rest_framework.test import APIClient
from recruitment.models import User, Applicant, Job, Application


class EmailFailureDoesNotBreakRequests(TestCase):
    """If SMTP fails, the action that already succeeded must still report success."""

    def test_registration_succeeds_even_if_verification_email_fails(self):
        client = APIClient()
        with mock.patch("recruitment.views.send_mail", side_effect=OSError("SMTP unreachable")):
            with self.assertLogs("recruitment.views", level="ERROR"):
                resp = client.post("/api/applicants/register/", {
                    "full_name": "Tunga Test",
                    "email": "tunga@example.com",
                    "password": "SomePass123",
                }, format="json")
        print(f"[EMAIL-RESILIENCE] Register with broken SMTP -> HTTP {resp.status_code}")
        self.assertEqual(resp.status_code, 201, resp.content)
        applicant = Applicant.objects.get(email="tunga@example.com")
        self.assertTrue(applicant.verification_token)

    def test_status_change_succeeds_even_if_notification_email_fails(self):
        hr = User.objects.create_user(username="hr_mailfail", password="Passw0rd!123", role="hr")
        applicant = Applicant.objects.create(
            full_name="A B", email="ab@example.com", password="x", is_verified=True, is_active=True,
        )
        job = Job.objects.create(title="Role", description="d", requirements="x",
                                  deadline="2027-01-31", posted_by=hr)
        app = Application.objects.create(job=job, applicant=applicant, cv_file="cvs/x.pdf",
                                          cv_text="x", fit_score=10.0, status="Applied")
        client = APIClient()
        client.force_authenticate(user=hr)
        with mock.patch("recruitment.views.send_mail", side_effect=OSError("SMTP unreachable")):
            with self.assertLogs("recruitment.views", level="ERROR"):
                resp = client.patch(f"/api/applications/{app.id}/status/", {"status": "Shortlisted"}, format="json")
        print(f"[EMAIL-RESILIENCE] Status change with broken SMTP -> HTTP {resp.status_code}")
        self.assertEqual(resp.status_code, 200, resp.content)
        app.refresh_from_db()
        self.assertEqual(app.status, "Shortlisted")
