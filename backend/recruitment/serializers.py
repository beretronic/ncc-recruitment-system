from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import User, Applicant, Job, Application, StatusAuditLog, Interview, JobDeletionRequest


class ApplicantRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Applicant
        fields = [
            "id", "full_name", "email", "password", "phone", "address",
            "date_of_birth", "gender", "education_level",
            "years_of_experience", "national_id_number",
        ]

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])
        return Applicant.objects.create(**validated_data)


class ApplicantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Applicant
        fields = [
            "id", "full_name", "email", "phone", "address", "date_of_birth",
            "gender", "education_level", "years_of_experience",
            "national_id_number", "is_verified", "created_at",
        ]


class JobSerializer(serializers.ModelSerializer):
    posted_by_name = serializers.CharField(source="posted_by.username", read_only=True)
    updated_by_name = serializers.CharField(source="updated_by.username", read_only=True, default=None)
    deletion_pending = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id", "title", "description", "requirements", "location",
            "deadline", "status", "posted_by", "posted_by_name",
            "created_at", "updated_by", "updated_by_name", "updated_at",
            "deletion_pending",
        ]
        read_only_fields = ["posted_by", "created_at", "updated_by", "updated_at"]

    def get_deletion_pending(self, obj):
        # .all() uses the prefetch set up in JobViewSet.get_queryset (no N+1 queries)
        return any(r.status == "pending" for r in obj.deletion_requests.all())


class JobDeletionRequestSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source="requested_by.username", read_only=True, default=None)
    decided_by_name = serializers.CharField(source="decided_by.username", read_only=True, default=None)
    application_count = serializers.SerializerMethodField()

    class Meta:
        model = JobDeletionRequest
        fields = [
            "id", "job", "job_title", "reason", "status",
            "requested_by", "requested_by_name", "requested_at",
            "decided_by", "decided_by_name", "decided_at", "application_count",
        ]
        read_only_fields = fields

    def get_application_count(self, obj):
        # How many applications would be wiped along with the vacancy.
        return obj.job.applications.count() if obj.job_id else 0


class ApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ["id", "job", "cv_file"]

    def validate_cv_file(self, value):
        if not value.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("Only PDF files are accepted.")
        if value.content_type != "application/pdf":
            raise serializers.ValidationError("Only PDF files are accepted.")
        return value


class ApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)
    applicant_name = serializers.CharField(source="applicant.full_name", read_only=True)
    interview_date = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "id", "job", "job_title", "applicant", "applicant_name",
            "cv_file", "fit_score", "status", "applied_at", "updated_at",
            "interview_date",
        ]
        read_only_fields = ["fit_score", "status", "applied_at", "updated_at", "interview_date"]

    def get_interview_date(self, obj):
        interview = obj.interviews.order_by("-date_time").first()
        return interview.date_time if interview else None


class StatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Application.STATUS_CHOICES)


class BulkStatusUpdateSerializer(serializers.Serializer):
    application_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    status = serializers.ChoiceField(choices=Application.STATUS_CHOICES)


class StatusAuditLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.username", read_only=True, default=None)

    class Meta:
        model = StatusAuditLog
        fields = ["id", "application", "old_status", "new_status", "changed_by", "changed_by_name", "timestamp"]


class InterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interview
        fields = ["id", "application", "date_time", "notes"]


class JobRecommendationSerializer(serializers.Serializer):
    job = JobSerializer()
    match_score = serializers.FloatField()


class LeaderboardEntrySerializer(serializers.Serializer):
    application_id = serializers.IntegerField()
    applicant_name = serializers.CharField()
    job_title = serializers.CharField()
    fit_score = serializers.FloatField(allow_null=True)
    status = serializers.CharField()


class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "is_active", "date_joined"]
        read_only_fields = ["date_joined"]


class StaffCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password", "role"]

    def validate_role(self, value):
        if value not in ("admin", "hr"):
            raise serializers.ValidationError("Role must be 'admin' or 'hr'.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.is_staff = True  # allows Django admin access too, if ever needed
        user.save()
        return user


class StaffUpdateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=False)
    role = serializers.ChoiceField(choices=[("admin", "Admin"), ("hr", "HR")], required=False)


class ApplicantAdminSerializer(serializers.ModelSerializer):
    application_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Applicant
        fields = [
            "id", "full_name", "email", "phone", "is_verified", "is_active",
            "created_at", "application_count",
        ]


class ApplicantAdminUpdateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=False)
    is_verified = serializers.BooleanField(required=False)
