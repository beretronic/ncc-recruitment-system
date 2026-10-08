from django.test import TestCase
from rest_framework.test import APIClient
from recruitment.models import User, Applicant, Job, Application, JobDeletionRequest


class DeletionApprovalWorkflow(TestCase):
    def setUp(self):
        self.hr = User.objects.create_user(username="hr_del", password="Passw0rd!123", role="hr")
        self.admin = User.objects.create_user(username="admin_del", password="Passw0rd!123", role="admin")
        self.job = Job.objects.create(title="Doomed Role", description="d", requirements="x",
                                      deadline="2099-01-31", posted_by=self.hr)
        applicant = Applicant.objects.create(full_name="A", email="a@example.com", password="x",
                                             is_verified=True, is_active=True)
        Application.objects.create(job=self.job, applicant=applicant, cv_file="cvs/x.pdf",
                                   cv_text="x", fit_score=1.0, status="Applied")
        self.hr_client = APIClient(); self.hr_client.force_authenticate(user=self.hr)
        self.admin_client = APIClient(); self.admin_client.force_authenticate(user=self.admin)

    def _request_deletion(self, reason="Posted by mistake"):
        return self.hr_client.post(f"/api/jobs/{self.job.id}/request-deletion/", {"reason": reason}, format="json")

    def test_hr_request_creates_pending_record_and_deletes_nothing(self):
        resp = self._request_deletion()
        print(f"[APPROVAL] HR requests deletion -> HTTP {resp.status_code}, status={resp.data['status']}")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertTrue(Job.objects.filter(id=self.job.id).exists())
        self.assertEqual(resp.data["application_count"], 1)
        listing = {j["id"]: j for j in self.hr_client.get("/api/jobs/").data}
        self.assertTrue(listing[self.job.id]["deletion_pending"])

    def test_reason_is_required(self):
        resp = self._request_deletion(reason="  ")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(JobDeletionRequest.objects.count(), 0)

    def test_cannot_stack_a_second_pending_request(self):
        self._request_deletion()
        resp = self._request_deletion()
        print(f"[APPROVAL] Duplicate request -> HTTP {resp.status_code}")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(JobDeletionRequest.objects.count(), 1)

    def test_admin_does_not_need_to_request(self):
        resp = self.admin_client.post(f"/api/jobs/{self.job.id}/request-deletion/", {"reason": "whatever"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_only_admin_can_see_and_decide_requests(self):
        req_id = self._request_deletion().data["id"]
        self.assertEqual(self.hr_client.get("/api/deletion-requests/").status_code, 403)
        self.assertEqual(self.hr_client.post(f"/api/deletion-requests/{req_id}/approve/").status_code, 403)
        self.assertEqual(APIClient().get("/api/deletion-requests/").status_code in (401, 403), True)
        self.assertTrue(Job.objects.filter(id=self.job.id).exists())

    def test_admin_sees_pending_request_with_details(self):
        self._request_deletion("Duplicate of another vacancy")
        resp = self.admin_client.get("/api/deletion-requests/")
        self.assertEqual(resp.status_code, 200)
        row = resp.data[0]
        print(f"[APPROVAL] Admin sees: '{row['job_title']}' by {row['requested_by_name']} - \"{row['reason']}\" ({row['application_count']} application(s))")
        self.assertEqual(row["job_title"], "Doomed Role")
        self.assertEqual(row["requested_by_name"], "hr_del")
        self.assertEqual(row["reason"], "Duplicate of another vacancy")

    def test_approve_deletes_vacancy_but_keeps_the_record(self):
        req_id = self._request_deletion().data["id"]
        resp = self.admin_client.post(f"/api/deletion-requests/{req_id}/approve/")
        print(f"[APPROVAL] Admin approves -> HTTP {resp.status_code}, status={resp.data['status']}")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(Job.objects.filter(id=self.job.id).exists())
        self.assertEqual(Application.objects.count(), 0)  # cascade, as warned
        req = JobDeletionRequest.objects.get(id=req_id)
        self.assertEqual(req.status, "approved")
        self.assertEqual(req.decided_by, self.admin)
        self.assertIsNotNone(req.decided_at)
        self.assertIsNone(req.job)
        self.assertEqual(req.job_title, "Doomed Role")  # permanent record survives
        self.assertEqual(self.admin_client.get("/api/deletion-requests/").data, [])

    def test_reject_keeps_vacancy_and_allows_a_new_request(self):
        req_id = self._request_deletion().data["id"]
        resp = self.admin_client.post(f"/api/deletion-requests/{req_id}/reject/")
        print(f"[APPROVAL] Admin rejects -> HTTP {resp.status_code}, status={resp.data['status']}")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Job.objects.filter(id=self.job.id).exists())
        self.assertEqual(Application.objects.count(), 1)
        listing = {j["id"]: j for j in self.hr_client.get("/api/jobs/").data}
        self.assertFalse(listing[self.job.id]["deletion_pending"])
        self.assertEqual(self._request_deletion("Trying again").status_code, 201)

    def test_a_request_cannot_be_decided_twice(self):
        req_id = self._request_deletion().data["id"]
        self.admin_client.post(f"/api/deletion-requests/{req_id}/reject/")
        resp = self.admin_client.post(f"/api/deletion-requests/{req_id}/approve/")
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(Job.objects.filter(id=self.job.id).exists())

    def test_admin_direct_delete_still_works_and_closes_out_pending_request(self):
        req_id = self._request_deletion().data["id"]
        resp = self.admin_client.delete(f"/api/jobs/{self.job.id}/")
        print(f"[APPROVAL] Admin deletes directly -> HTTP {resp.status_code}")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Job.objects.filter(id=self.job.id).exists())
        req = JobDeletionRequest.objects.get(id=req_id)
        self.assertEqual(req.status, "approved")
        self.assertEqual(req.decided_by, self.admin)

    def test_full_history_available_to_admin(self):
        req_id = self._request_deletion().data["id"]
        self.admin_client.post(f"/api/deletion-requests/{req_id}/reject/")
        self.assertEqual(self.admin_client.get("/api/deletion-requests/").data, [])
        history = self.admin_client.get("/api/deletion-requests/?status=all").data
        self.assertEqual([h["status"] for h in history], ["rejected"])
