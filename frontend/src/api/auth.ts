import { api, setStaffTokens, setApplicantTokens } from "./client";
import type { Applicant } from "../types";

// ---- HR / Admin (Django User via simplejwt) ----

export async function staffLogin(username: string, password: string) {
  const res = await api.post("/token/", { username, password });
  setStaffTokens(res.data.access, res.data.refresh);
  return res.data;
}

// ---- Applicant ----

export interface ApplicantRegisterPayload {
  full_name: string;
  email: string;
  password: string;
  phone?: string;
  address?: string;
  date_of_birth?: string;
  gender?: string;
  education_level?: string;
  years_of_experience?: number;
  national_id_number?: string;
}

export async function applicantRegister(payload: ApplicantRegisterPayload) {
  const res = await api.post("/applicants/register/", payload);
  return res.data;
}

export async function applicantVerify(token: string) {
  const res = await api.post("/applicants/verify/", { token });
  return res.data;
}

export async function applicantLogin(email: string, password: string) {
  const res = await api.post("/applicants/login/", { email, password });
  setApplicantTokens(res.data.access, res.data.refresh);
  return res.data;
}

export async function getApplicantMe(): Promise<Applicant> {
  const res = await api.get("/applicants/me/");
  return res.data;
}
