import { api } from "./client";
import type { StaffMember, ApplicantAdmin, AdminSummary } from "../types";

export async function getStaffMe(): Promise<StaffMember> {
  const res = await api.get("/staff/me/");
  return res.data;
}

export async function listStaff(): Promise<StaffMember[]> {
  const res = await api.get("/staff/");
  return res.data;
}

export interface StaffCreatePayload {
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  password: string;
  role: "admin" | "hr";
}

export async function createStaff(payload: StaffCreatePayload): Promise<StaffMember> {
  const res = await api.post("/staff/", payload);
  return res.data;
}

export async function updateStaff(
  staffId: number,
  data: { is_active?: boolean; role?: "admin" | "hr" }
): Promise<StaffMember> {
  const res = await api.patch(`/staff/${staffId}/`, data);
  return res.data;
}

export async function listApplicantsAdmin(): Promise<ApplicantAdmin[]> {
  const res = await api.get("/admin/applicants/");
  return res.data;
}

export async function updateApplicantAdmin(
  applicantId: number,
  data: { is_active?: boolean; is_verified?: boolean }
) {
  const res = await api.patch(`/admin/applicants/${applicantId}/`, data);
  return res.data;
}

export async function getAdminSummary(): Promise<AdminSummary> {
  const res = await api.get("/admin/summary/");
  return res.data;
}
