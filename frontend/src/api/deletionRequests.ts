import { api } from "./client";

export interface DeletionRequest {
  id: number;
  job: number | null;
  job_title: string;
  reason: string;
  status: "pending" | "approved" | "rejected";
  requested_by_name?: string | null;
  requested_at: string;
  decided_by_name?: string | null;
  decided_at?: string | null;
  application_count: number;
}

// HR: ask for a vacancy to be deleted (nothing is deleted until an Admin approves).
export async function requestJobDeletion(jobId: number, reason: string): Promise<DeletionRequest> {
  const res = await api.post(`/jobs/${jobId}/request-deletion/`, { reason });
  return res.data;
}

// Admin: pending requests.
export async function listDeletionRequests(): Promise<DeletionRequest[]> {
  const res = await api.get("/deletion-requests/");
  return res.data;
}

export async function approveDeletionRequest(id: number): Promise<DeletionRequest> {
  const res = await api.post(`/deletion-requests/${id}/approve/`);
  return res.data;
}

export async function rejectDeletionRequest(id: number): Promise<DeletionRequest> {
  const res = await api.post(`/deletion-requests/${id}/reject/`);
  return res.data;
}

// Pull a readable message out of an API error response.
export function apiErrorMessage(err: unknown, fallback: string): string {
  const data = (err as { response?: { data?: { detail?: string; reason?: string[] } } })?.response?.data;
  return data?.detail || data?.reason?.[0] || fallback;
}
