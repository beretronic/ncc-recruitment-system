from unittest import mock

from django.core import mail
from rest_framework.test import APIClient
from django.test import TestCase

from recruitment.models import User, Applicant, Job, Application, Interview


class ScheduleInterviewSendsEmail(TestCase):
    def setUp(self):
        self.hr = User.objects.create_user(username="hr_sched", password="Passw0rd!123", role="hr")
        self.applicant = Applicant.objects.create(full_name="Chipo Moyo", email="chipo@example.com",
                                                  password="x", is_verified=True, is_active=True)
        self.job = Job.objects.create(title="IT Attache", description="d", requirements="x",
                                      deadline="2099-01-31", posted_by=self.hr)
        self.app = Application.objects.create(job=self.job, applicant=self.applicant,
                                              cv_file="cvs/x.pdf", cv_text="x", fit_score=5.0,
                                              status="Applied")
        self.client = APIClient()
        self.client.force_authenticate(user=self.hr)
        mail.outbox = []

    def schedule(self, when="2027-03-10T09:30:00"):
        return self.client.post("/api/interviews/", {
            "application": self.app.id, "date_time": when, "notes": "Bring your ID",
        }, format="json")

    def test_scheduling_from_a_earlier_stage_changes_status_and_emails_the_chosen_date(self):
        resp = self.schedule()
        self.assertEqual(resp.status_code, 201, resp.content)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, "Interview")
        self.assertEqual(len(mail.outbox), 1)
        print(f"[SCHEDULE] From 'Applied' -> email: {mail.outbox[0].body}")
        self.assertIn("10 March 2027 at 09:30", mail.outbox[0].body)

    def test_scheduling_when_already_at_interview_still_emails_the_applicant(self):
        # HR clicks "Move to Interview" first (auto-schedules + emails)...
        self.client.patch(f"/api/applications/{self.app.id}/status/", {"status": "Interview"}, format="json")
        self.assertEqual(len(mail.outbox), 1)
        mail.outbox = []
        # ...then "Schedule Interview" to pick the real date. This used to send nothing.
        resp = self.schedule()
        self.assertEqual(resp.status_code, 201, resp.content)
        print(f"[SCHEDULE] Already at 'Interview' -> emails sent: {len(mail.outbox)}")
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        print(f"[SCHEDULE] Email: {body}")
        self.assertIn("10 March 2027 at 09:30", body)
        self.assertIn("rescheduled", mail.outbox[0].subject.lower() + body.lower())

    def test_the_manually_chosen_date_is_used_even_if_earlier_than_the_auto_date(self):
        self.client.patch(f"/api/applications/{self.app.id}/status/", {"status": "Interview"}, format="json")
        mail.outbox = []
        self.schedule("2026-12-01T08:00:00")  # earlier than the auto-scheduled "7 days from now" date? whichever -- must be the one chosen
        self.assertIn("01 December 2026 at 08:00", mail.outbox[0].body)

    def test_scheduling_still_succeeds_if_the_email_cannot_be_sent(self):
        with mock.patch("recruitment.views.send_mail", side_effect=OSError("SMTP blocked")):
            with self.assertLogs("recruitment.views", level="ERROR"):
                resp = self.schedule()
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(Interview.objects.filter(application=self.app).count(), 1)
