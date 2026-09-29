import { api } from "./client";
import type {
  Application,
  StatusAuditLogEntry,
  JobRecommendation,
  DashboardSummary,
  LeaderboardEntry,
  ApplicationStatus,
} from "../types";

// ---- Applicant-facing ----

export async function submitApplication(jobId: number, cvFile: File): Promise<Application> {
  const formData = new FormData();
  formData.append("job", String(jobId));
  formData.append("cv_file", cvFile);
  const res = await api.post("/applications/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function myApplications(): Promise<Application[]> {
  const res = await api.get("/applications/mine/");
  return res.data;
}

export async function getRecommendations(): Promise<JobRecommendation[]> {
  const res = await api.get("/recommendations/");
  return res.data;
}

// ---- HR/Admin-facing ----

export async function jobApplications(jobId: number): Promise<Application[]> {
  const res = await api.get(`/jobs/${jobId}/applications/`);
  return res.data;
}

export async function getApplication(applicationId: number): Promise<Application> {
  const res = await api.get(`/applications/${applicationId}/`);
  return res.data;
}

export async function updateApplicationStatus(
  applicationId: number,
  status: ApplicationStatus
): Promise<Application> {
  const res = await api.patch(`/applications/${applicationId}/status/`, { status });
  return res.data;
}

export async function bulkUpdateStatus(
  applicationIds: number[],
  status: ApplicationStatus
): Promise<Application[]> {
  const res = await api.post("/applications/bulk-status/", {
    application_ids: applicationIds,
    status,
  });
  return res.data;
}

export async function getAuditLog(applicationId: number): Promise<StatusAuditLogEntry[]> {
  const res = await api.get(`/applications/${applicationId}/audit-log/`);
  return res.data;
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const res = await api.get("/dashboard/summary/");
  return res.data;
}

export async function getJobLeaderboard(jobId: number, limit = 10): Promise<LeaderboardEntry[]> {
  const res = await api.get(`/jobs/${jobId}/leaderboard/?limit=${limit}`);
  return res.data;
}

export async function scheduleInterview(applicationId: number, dateTime: string, notes: string) {
  const res = await api.post("/interviews/", {
    application: applicationId,
    date_time: dateTime,
    notes,
  });
  return res.data;
}
