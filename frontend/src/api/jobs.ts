import { api } from "./client";
import type { Job } from "../types";

export async function listJobs(): Promise<Job[]> {
  const res = await api.get("/jobs/");
  return res.data;
}

export async function getJob(id: number): Promise<Job> {
  const res = await api.get(`/jobs/${id}/`);
  return res.data;
}

export interface JobPayload {
  title: string;
  description: string;
  requirements: string;
  location: string;
  deadline: string;
}

export async function createJob(payload: JobPayload): Promise<Job> {
  const res = await api.post("/jobs/", payload);
  return res.data;
}

export async function updateJob(id: number, payload: Partial<JobPayload & { status: string }>): Promise<Job> {
  const res = await api.patch(`/jobs/${id}/`, payload);
  return res.data;
}

export async function deleteJob(id: number): Promise<void> {
  await api.delete(`/jobs/${id}/`);
}
