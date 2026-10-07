from django.test import TestCase
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient
from recruitment.models import User, Applicant, Job, Application, Interview


class AutoInterviewScheduling(TestCase):
    def setUp(self):
        self.hr = User.objects.create_user(username="hr1", password="Passw0rd!123", role="hr")
        self.applicant = Applicant.objects.create(
            full_name="Test Person", email="test@example.com", password="x", is_verified=True, is_active=True,
        )
        self.job = Job.objects.create(title="Analyst", description="d", requirements="x",
                                       deadline="2027-01-31", posted_by=self.hr)
        self.app = Application.objects.create(
            job=self.job, applicant=self.applicant, cv_file="cvs/x.pdf",
            cv_text="x", fit_score=50.0, status="Applied",
        )

    def test_interview_auto_scheduled_7_days_at_0800(self):
        mail.outbox = []
        before = timezone.localtime(timezone.now())
        client = APIClient()
        client.force_authenticate(user=self.hr)
        resp = client.patch(f"/api/applications/{self.app.id}/status/", {"status": "Interview"}, format="json")
        self.assertEqual(resp.status_code, 200)

        interview = Interview.objects.get(application=self.app)
        print(f"[INTERVIEW] Auto-scheduled for: {interview.date_time}")
        self.assertEqual(interview.date_time.astimezone(before.tzinfo).hour, 8)
        self.assertEqual(interview.date_time.astimezone(before.tzinfo).minute, 0)
        self.assertEqual((interview.date_time.date() - before.date()).days, 7)

        self.assertEqual(len(mail.outbox), 1)
        print(f"[INTERVIEW] Email body: {mail.outbox[0].body}")
        self.assertIn("interview has been scheduled", mail.outbox[0].body)
        self.assertIn("08:00", mail.outbox[0].body)
