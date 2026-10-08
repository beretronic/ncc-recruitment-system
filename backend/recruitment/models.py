from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Admin and HR accounts only. Applicants use the separate Applicant model."""
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("hr", "HR"),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    # is_active already exists on AbstractUser - used here for soft delete


class Applicant(models.Model):
    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)  # store hashed password
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    education_level = models.CharField(max_length=100, blank=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    national_id_number = models.CharField(max_length=50, blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)  # Admin can suspend an applicant account
    verification_token = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class Job(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("closed", "Closed"),
    ]
    title = models.CharField(max_length=150)
    description = models.TextField()
    requirements = models.TextField()
    location = models.CharField(max_length=150, blank=True)
    deadline = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="jobs")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="jobs_updated"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Application(models.Model):
    STATUS_CHOICES = [
        ("Applied", "Applied"),
        ("Shortlisted", "Shortlisted"),
        ("Interview", "Interview"),
        ("Hired", "Hired"),
        ("Rejected", "Rejected"),
    ]
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE, related_name="applications")
    cv_file = models.FileField(upload_to="cvs/")
    cv_text = models.TextField(blank=True)  # extracted via pdfplumber
    fit_score = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Applied")
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("job", "applicant")  # prevents duplicate applications at the DB level

    def __str__(self):
        return f"{self.applicant.full_name} -> {self.job.title}"


class Interview(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="interviews")
    date_time = models.DateTimeField()
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Interview for {self.application}"


class StatusAuditLog(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="status_logs")
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application} : {self.old_status} -> {self.new_status}"


class JobDeletionRequest(models.Model):
    """
    HR cannot delete a vacancy directly (deleting also wipes every application,
    interview and audit-log row linked to it). Instead HR raises a request that
    an Admin approves or rejects. The request row is kept permanently as a record
    of who asked, why, and who decided -- so `job` is SET_NULL (the request
    outlives the vacancy) and the title is snapshotted.
    """
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True,
                            related_name="deletion_requests")
    job_title = models.CharField(max_length=150)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                     related_name="deletion_requests_made")
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="deletion_requests_decided")
    decided_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Deletion request for '{self.job_title}' ({self.status})"
