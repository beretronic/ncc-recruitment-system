from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField, Q
from django.utils import timezone
from .models import Job, Application


def get_applicants_per_job():
    return list(
        Job.objects.annotate(applicant_count=Count("applications"))
        .values("id", "title", "applicant_count")
        .order_by("-applicant_count")
    )


def get_status_funnel():
    """Count of applications at each pipeline stage, across the whole system."""
    counts = (
        Application.objects.values("status")
        .annotate(count=Count("id"))
        .order_by()
    )
    # ensure every status appears even if count is 0
    all_statuses = [c for c, _ in Application.STATUS_CHOICES]
    result = {s: 0 for s in all_statuses}
    for row in counts:
        result[row["status"]] = row["count"]
    return result


def get_time_to_hire():
    """
    Average number of days between an application being submitted (applied_at)
    and it reaching 'Hired' status (approximated using updated_at on hired records,
    since we don't store a separate hired_at timestamp).
    """
    hired = Application.objects.filter(status="Hired").annotate(
        duration=ExpressionWrapper(F("updated_at") - F("applied_at"), output_field=DurationField())
    )
    agg = hired.aggregate(avg_duration=Avg("duration"))
    avg_duration = agg["avg_duration"]
    if avg_duration is None:
        return None
    return round(avg_duration.total_seconds() / 86400, 1)  # days


def get_top_candidates(job_id=None, limit=10):
    """Top candidates by fit_score, either for one job or globally."""
    qs = Application.objects.select_related("applicant", "job").exclude(fit_score__isnull=True)
    if job_id:
        qs = qs.filter(job_id=job_id)
    qs = qs.order_by("-fit_score")[:limit]
    return [
        {
            "application_id": a.id,
            "applicant_name": a.applicant.full_name,
            "job_title": a.job.title,
            "fit_score": a.fit_score,
            "status": a.status,
        }
        for a in qs
    ]


def get_dashboard_summary():
    total_applicants = Application.objects.values("applicant_id").distinct().count()
    total_jobs_open = Job.objects.filter(status="open").count()
    total_jobs_closed = Job.objects.filter(status="closed").count()
    total_applications = Application.objects.count()

    return {
        "total_applicants": total_applicants,
        "total_jobs_open": total_jobs_open,
        "total_jobs_closed": total_jobs_closed,
        "total_applications": total_applications,
        "applicants_per_job": get_applicants_per_job(),
        "status_funnel": get_status_funnel(),
        "avg_time_to_hire_days": get_time_to_hire(),
        "top_candidates_global": get_top_candidates(limit=10),
    }
