import io
import threading
import time
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from recruitment.authentication import issue_applicant_token
from recruitment.models import User, Applicant, Job, Application, ApplicationCV, StatusAuditLog


def make_pdf_bytes(text="Some CV text about Python and Django"):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(50, 750, text)
    c.save()
    return buf.getvalue()


def pdf_upload(data, name="cv.pdf"):
    f = io.BytesIO(data)
    f.name = name
    return f


class ApplyAndCVStorage(TestCase):
    def setUp(self):
        self.hr = User.objects.create_user(username="hr_cv", password="Passw0rd!123", role="hr")
        self.job = Job.objects.create(title="Developer", description="d", requirements="python django",
                                      deadline="2099-01-31", posted_by=self.hr)
        self.applicant = Applicant.objects.create(full_name="Owner One", email="owner@example.com",
                                                  password="x", is_verified=True, is_active=True)
        self.other = Applicant.objects.create(full_name="Someone Else", email="other@example.com",
                                              password="x", is_verified=True, is_active=True)
        self.pdf = make_pdf_bytes()

    def client_for(self, applicant):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_applicant_token(applicant)['access']}")
        return c

    def apply(self, client=None, data=None):
        client = client or self.client_for(self.applicant)
        return client.post("/api/applications/",
                           {"job": self.job.id, "cv_file": pdf_upload(data or self.pdf)}, format="multipart")

    # ---- complaint 1: "could not apply, then already applied" ----
    def test_apply_succeeds_even_when_the_confirmation_email_fails(self):
        with mock.patch("recruitment.views.send_mail", side_effect=OSError("SMTP blocked")):
            with self.assertLogs("recruitment.views", level="ERROR"):
                resp = self.apply()
        print(f"[APPLY] Apply while SMTP is broken -> HTTP {resp.status_code}")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(Application.objects.count(), 1)

    def test_a_failure_part_way_leaves_no_half_created_application(self):
        client = self.client_for(self.applicant)
        client.raise_request_exception = False
        with mock.patch.object(StatusAuditLog.objects, "create", side_effect=RuntimeError("boom")):
            resp = self.apply(client)
        print(f"[APPLY] Failure mid-way -> HTTP {resp.status_code}, applications left: {Application.objects.count()}")
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(Application.objects.count(), 0)
        self.assertEqual(ApplicationCV.objects.count(), 0)
        self.assertEqual(self.apply().status_code, 201)  # the retry works cleanly

    # ---- complaint 2: CV not displaying ----
    def test_cv_is_stored_in_the_database_and_hr_can_open_it(self):
        self.apply()
        app = Application.objects.get()
        self.assertEqual(ApplicationCV.objects.get(application=app).data.__len__(), len(self.pdf))
        hr = APIClient(); hr.force_authenticate(user=self.hr)
        resp = hr.get(f"/api/applications/{app.id}/cv/")
        print(f"[CV] HR opens CV -> HTTP {resp.status_code}, {resp['Content-Type']}, {len(resp.content)} bytes")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertEqual(resp.content, self.pdf)

    def test_cv_survives_the_disk_being_wiped(self):
        self.apply()
        app = Application.objects.get()
        app.cv_file.storage.delete(app.cv_file.name)  # what Render's ephemeral disk does on sleep/redeploy
        hr = APIClient(); hr.force_authenticate(user=self.hr)
        resp = hr.get(f"/api/applications/{app.id}/cv/")
        print(f"[CV] After the on-disk file is deleted -> HTTP {resp.status_code}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, self.pdf)

    def test_applicant_can_open_their_own_cv_but_not_anyone_elses(self):
        self.apply()
        app = Application.objects.get()
        self.assertEqual(self.client_for(self.applicant).get(f"/api/applications/{app.id}/cv/").status_code, 200)
        resp = self.client_for(self.other).get(f"/api/applications/{app.id}/cv/")
        print(f"[CV] Another applicant tries to open it -> HTTP {resp.status_code}")
        self.assertEqual(resp.status_code, 403)
        self.assertIn(APIClient().get(f"/api/applications/{app.id}/cv/").status_code, (401, 403))

    def test_cv_that_is_truly_gone_reports_a_clear_404(self):
        app = Application.objects.create(job=self.job, applicant=self.applicant, cv_file="cvs/nope.pdf",
                                         cv_text="x", fit_score=1.0, status="Applied")
        hr = APIClient(); hr.force_authenticate(user=self.hr)
        resp = hr.get(f"/api/applications/{app.id}/cv/")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("no longer available", resp.data["detail"])

    def test_oversized_cv_is_rejected(self):
        resp = self.apply(data=make_pdf_bytes() + b"0" * (5 * 1024 * 1024 + 1))
        print(f"[CV] 5MB+ upload -> HTTP {resp.status_code}")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Application.objects.count(), 0)


class EmailsNeverBlockTheRequest(TestCase):
    """complaint 3: emails must not be able to stall or break a request."""

    @override_settings(EMAIL_SEND_IN_BACKGROUND=True)
    def test_slow_smtp_does_not_delay_the_response(self):
        release = threading.Event()
        with mock.patch("recruitment.views.send_mail", side_effect=lambda *a, **k: release.wait(5)):
            start = time.monotonic()
            resp = APIClient().post("/api/applicants/register/", {
                "full_name": "Slow Mail", "email": "slow@example.com", "password": "SomePass123",
            }, format="json")
            elapsed = time.monotonic() - start
            release.set()
        print(f"[EMAIL] Register while SMTP stalls -> HTTP {resp.status_code} in {elapsed:.2f}s")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertLess(elapsed, 2.0)

    @override_settings(EMAIL_SEND_IN_BACKGROUND=True)
    def test_email_is_still_delivered_from_the_background_thread(self):
        mail.outbox = []
        APIClient().post("/api/applicants/register/", {
            "full_name": "Bg Mail", "email": "bg@example.com", "password": "SomePass123",
        }, format="json")
        deadline = time.monotonic() + 3
        while not mail.outbox and time.monotonic() < deadline:
            time.sleep(0.05)
        print(f"[EMAIL] Delivered from background thread: {[m.to for m in mail.outbox]}")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["bg@example.com"])
