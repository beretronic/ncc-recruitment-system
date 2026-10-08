from django.test import TestCase
from rest_framework.test import APIClient
from recruitment.models import User, Applicant, Job
from recruitment.authentication import issue_applicant_token


class JobVisibilityAndDeletion(TestCase):
    def setUp(self):
        self.hr = User.objects.create_user(username="hr_vis", password="Passw0rd!123", role="hr")
        self.open_job = Job.objects.create(title="Open Role", description="d", requirements="x",
                                           deadline="2099-01-31", posted_by=self.hr, status="open")
        self.closed_job = Job.objects.create(title="Closed Role", description="d", requirements="x",
                                             deadline="2099-01-31", posted_by=self.hr, status="closed")
        self.applicant = Applicant.objects.create(
            full_name="Logged In Applicant", email="li@example.com", password="x",
            is_verified=True, is_active=True,
        )

    def _applicant_client(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_applicant_token(self.applicant)['access']}")
        return c

    def test_logged_in_applicant_does_not_see_closed_vacancies(self):
        resp = self._applicant_client().get("/api/jobs/")
        titles = [j["title"] for j in resp.data]
        print(f"[VISIBILITY] Logged-in applicant sees: {titles}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Open Role", titles)
        self.assertNotIn("Closed Role", titles)

    def test_logged_in_applicant_cannot_open_closed_vacancy_directly(self):
        resp = self._applicant_client().get(f"/api/jobs/{self.closed_job.id}/")
        print(f"[VISIBILITY] Applicant opening closed job directly -> HTTP {resp.status_code}")
        self.assertEqual(resp.status_code, 404)

    def test_anonymous_visitor_does_not_see_closed_vacancies(self):
        titles = [j["title"] for j in APIClient().get("/api/jobs/").data]
        self.assertNotIn("Closed Role", titles)

    def test_hr_still_sees_closed_vacancies_so_they_can_reopen_them(self):
        c = APIClient(); c.force_authenticate(user=self.hr)
        titles = [j["title"] for j in c.get("/api/jobs/").data]
        print(f"[VISIBILITY] HR sees: {titles}")
        self.assertIn("Closed Role", titles)
        self.assertIn("Open Role", titles)

    def test_hr_cannot_delete_a_vacancy_directly(self):
        # Deleting is Admin-only now; HR must raise a deletion request instead.
        c = APIClient(); c.force_authenticate(user=self.hr)
        resp = c.delete(f"/api/jobs/{self.closed_job.id}/")
        print(f"[DELETE] HR tries to delete directly -> HTTP {resp.status_code}")
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Job.objects.filter(id=self.closed_job.id).exists())

    def test_applicant_cannot_delete_a_vacancy(self):
        resp = self._applicant_client().delete(f"/api/jobs/{self.open_job.id}/")
        print(f"[DELETE] Applicant tries to delete vacancy -> HTTP {resp.status_code}")
        self.assertIn(resp.status_code, (401, 403))
        self.assertTrue(Job.objects.filter(id=self.open_job.id).exists())
