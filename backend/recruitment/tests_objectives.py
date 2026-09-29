"""
Functional tests mapped to the 5 project objectives (Chapter 1.5):
  1. Centralised job posting + online application submission
  2. Automatic status tracking through the recruitment pipeline
  3. TF-IDF + cosine similarity fit scoring / ranking
  4. Email notification on status change
  5. Time-stamped audit log of status changes

Run with:
DJANGO_SETTINGS_MODULE=ncc_recruitment.test_settings python manage.py test recruitment.tests_objectives -v 2
"""
import io
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status as http_status

from recruitment.models import User, Applicant, Job, Application, StatusAuditLog
from recruitment.authentication import issue_applicant_token


def make_pdf_bytes(text: str) -> bytes:
    """Build a minimal valid single-page PDF whose content stream is the given text."""
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    textobject = c.beginText(50, 750)
    for line in text.split("\n"):
        textobject.textLine(line)
    c.drawText(textobject)
    c.save()
    return buf.getvalue()


class ObjectiveOneJobPostingAndApplication(TestCase):
    """Objective 1: centralised platform for posting vacancies + submitting applications online."""

    def setUp(self):
        self.client = APIClient()
        self.hr = User.objects.create_user(username="hr_jane", password="Passw0rd!123", role="hr")
        self.applicant = Applicant.objects.create(
            full_name="Tendai Moyo", email="tendai@example.com",
            password="hashed", is_verified=True, is_active=True,
        )

    def test_hr_can_post_job_and_applicant_can_apply(self):
        self.client.force_authenticate(user=self.hr)
        resp = self.client.post("/api/jobs/", {
            "title": "Policy Analyst",
            "description": "Analyse competitiveness policy data.",
            "requirements": "Economics degree, data analysis, Python, statistics",
            "location": "Harare",
            "deadline": "2027-01-31",
        }, format="json")
        self.assertEqual(resp.status_code, http_status.HTTP_201_CREATED, resp.content)
        job_id = resp.data["id"]
        print(f"\n[OBJ1] Job posted -> id={job_id}, title={resp.data['title']}, status={resp.data['status']}")

        self.client.force_authenticate(user=None)  # clear the HR force_authenticate first
        tokens = issue_applicant_token(self.applicant)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        cv = make_pdf_bytes("Tendai Moyo\nEconomics graduate. Skilled in Python, statistics and data analysis.")
        cv_upload = io.BytesIO(cv)
        cv_upload.name = "tendai_cv.pdf"
        resp2 = self.client.post("/api/applications/", {"job": job_id, "cv_file": cv_upload}, format="multipart")
        self.assertEqual(resp2.status_code, http_status.HTTP_201_CREATED, resp2.content)
        print(f"[OBJ1] Application submitted -> id={resp2.data['id']}, status={resp2.data['status']}, fit_score={resp2.data['fit_score']}")
        self.assertEqual(Application.objects.count(), 1)


class ObjectiveTwoStatusTracking(TestCase):
    """Objective 2: application status is tracked/updated automatically through the pipeline."""

    def setUp(self):
        self.hr = User.objects.create_user(username="hr_bob", password="Passw0rd!123", role="hr")
        self.applicant = Applicant.objects.create(
            full_name="Farai Chuma", email="farai@example.com", password="x", is_verified=True, is_active=True,
        )
        self.job = Job.objects.create(
            title="Research Officer", description="d", requirements="research, policy analysis",
            deadline="2027-01-31", posted_by=self.hr,
        )
        self.app = Application.objects.create(
            job=self.job, applicant=self.applicant, cv_file="cvs/x.pdf",
            cv_text="research policy analysis", fit_score=71.4, status="Applied",
        )

    def test_status_progresses_through_pipeline(self):
        client = APIClient()
        client.force_authenticate(user=self.hr)
        pipeline = ["Shortlisted", "Interview", "Hired"]
        for new_status in pipeline:
            resp = client.patch(f"/api/applications/{self.app.id}/status/", {"status": new_status}, format="json")
            self.assertEqual(resp.status_code, http_status.HTTP_200_OK, resp.content)
            self.app.refresh_from_db()
            self.assertEqual(self.app.status, new_status)
            print(f"[OBJ2] Status transition -> {new_status} confirmed (HTTP {resp.status_code})")


class ObjectiveThreeFitScoring(TestCase):
    """Objective 3: TF-IDF + cosine similarity scoring/ranking of applicants against job requirements."""

    def test_closer_matching_cv_scores_higher_and_ranking_is_correct(self):
        from recruitment.matching import compute_fit_score
        job_requirements = "Python developer with Django REST Framework and PostgreSQL experience"
        strong_cv = "Experienced Python developer skilled in Django REST Framework and PostgreSQL"
        weak_cv = "Graphic designer skilled in Adobe Photoshop and Illustrator"

        strong_score = compute_fit_score(strong_cv, job_requirements)
        weak_score = compute_fit_score(weak_cv, job_requirements)
        print(f"[OBJ3] Strong-match CV fit_score = {strong_score}")
        print(f"[OBJ3] Weak-match CV fit_score   = {weak_score}")
        self.assertGreater(strong_score, weak_score)
        self.assertGreaterEqual(strong_score, 30.0)
        self.assertLessEqual(weak_score, 15.0)

    def test_job_applications_endpoint_ranks_by_fit_score_desc(self):
        hr = User.objects.create_user(username="hr_rank", password="Passw0rd!123", role="hr")
        job = Job.objects.create(title="Data Analyst", description="d", requirements="python sql",
                                  deadline="2027-01-31", posted_by=hr)
        a1 = Applicant.objects.create(full_name="A One", email="a1@example.com", password="x", is_verified=True)
        a2 = Applicant.objects.create(full_name="A Two", email="a2@example.com", password="x", is_verified=True)
        Application.objects.create(job=job, applicant=a1, cv_file="cvs/1.pdf", cv_text="python sql", fit_score=85.0, status="Applied")
        Application.objects.create(job=job, applicant=a2, cv_file="cvs/2.pdf", cv_text="unrelated", fit_score=12.0, status="Applied")

        client = APIClient()
        client.force_authenticate(user=hr)
        resp = client.get(f"/api/jobs/{job.id}/applications/")
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        scores = [row["fit_score"] for row in resp.data]
        print(f"[OBJ3] Leaderboard order (fit_score desc) -> {scores}")
        self.assertEqual(scores, sorted(scores, reverse=True))


class ObjectiveFourEmailNotifications(TestCase):
    """Objective 4: applicants are notified by email whenever their application status changes."""

    def setUp(self):
        self.hr = User.objects.create_user(username="hr_mail", password="Passw0rd!123", role="hr")
        self.applicant = Applicant.objects.create(
            full_name="Rudo Banda", email="rudo@example.com", password="x", is_verified=True, is_active=True,
        )
        self.job = Job.objects.create(title="HR Officer", description="d", requirements="hr, recruitment",
                                       deadline="2027-01-31", posted_by=self.hr)
        self.app = Application.objects.create(
            job=self.job, applicant=self.applicant, cv_file="cvs/x.pdf",
            cv_text="hr recruitment", fit_score=60.0, status="Applied",
        )

    def test_email_sent_on_status_change(self):
        mail.outbox = []
        client = APIClient()
        client.force_authenticate(user=self.hr)
        resp = client.patch(f"/api/applications/{self.app.id}/status/", {"status": "Shortlisted"}, format="json")
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        print(f"[OBJ4] Email sent -> to={sent.to}, subject='{sent.subject}'")
        print(f"[OBJ4] Body: {sent.body}")
        self.assertIn("rudo@example.com", sent.to)
        self.assertIn("Shortlisted", sent.body)


class ObjectiveFiveAuditLog(TestCase):
    """Objective 5: maintain a time-stamped audit log of all application status changes."""

    def setUp(self):
        self.hr = User.objects.create_user(username="hr_audit", password="Passw0rd!123", role="hr")
        self.applicant = Applicant.objects.create(
            full_name="Kudzai Sibanda", email="kudzai@example.com", password="x", is_verified=True, is_active=True,
        )
        self.job = Job.objects.create(title="Compliance Officer", description="d", requirements="audit, compliance",
                                       deadline="2027-01-31", posted_by=self.hr)
        self.app = Application.objects.create(
            job=self.job, applicant=self.applicant, cv_file="cvs/x.pdf",
            cv_text="audit compliance", fit_score=55.0, status="Applied",
        )

    def test_audit_log_records_every_transition_with_timestamps(self):
        client = APIClient()
        client.force_authenticate(user=self.hr)
        for new_status in ["Shortlisted", "Interview", "Rejected"]:
            client.patch(f"/api/applications/{self.app.id}/status/", {"status": new_status}, format="json")

        logs = StatusAuditLog.objects.filter(application=self.app).order_by("timestamp")
        self.assertEqual(logs.count(), 3)
        for log in logs:
            print(f"[OBJ5] {log.timestamp.isoformat()} | {log.old_status or '(none)'} -> {log.new_status} | by {log.changed_by}")
        self.assertEqual([l.new_status for l in logs], ["Shortlisted", "Interview", "Rejected"])

        resp = client.get(f"/api/applications/{self.app.id}/audit-log/")
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 3)
