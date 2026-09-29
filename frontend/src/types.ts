export type Role = "admin" | "hr" | "applicant";

export interface Job {
  id: number;
  title: string;
  description: string;
  requirements: string;
  location: string;
  deadline: string;
  status: "open" | "closed";
  posted_by?: number;
  posted_by_name?: string;
  created_at: string;
  updated_by?: number | null;
  updated_by_name?: string | null;
  updated_at?: string;
}

export type ApplicationStatus =
  | "Applied"
  | "Shortlisted"
  | "Interview"
  | "Hired"
  | "Rejected";

export interface Application {
  id: number;
  job: number;
  job_title?: string;
  applicant: number;
  applicant_name?: string;
  cv_file: string;
  fit_score: number | null;
  status: ApplicationStatus;
  applied_at: string;
  updated_at: string;
  interview_date?: string | null;
}

export interface Applicant {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  address: string;
  date_of_birth: string | null;
  gender: string;
  education_level: string;
  years_of_experience: number;
  national_id_number: string;
  is_verified: boolean;
  created_at: string;
}

export interface StatusAuditLogEntry {
  id: number;
  application: number;
  old_status: string;
  new_status: string;
  changed_by: number | null;
  changed_by_name: string | null;
  timestamp: string;
}

export interface JobRecommendation {
  job: Job;
  match_score: number;
}

export interface DashboardSummary {
  total_applicants: number;
  total_jobs_open: number;
  total_jobs_closed: number;
  total_applications: number;
  applicants_per_job: { id: number; title: string; applicant_count: number }[];
  status_funnel: Record<ApplicationStatus, number>;
  avg_time_to_hire_days: number | null;
  top_candidates_global: LeaderboardEntry[];
}

export interface LeaderboardEntry {
  application_id: number;
  applicant_name: string;
  job_title: string;
  fit_score: number | null;
  status: ApplicationStatus;
}

// ---- Staff / Admin account management ----

export interface StaffMember {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: "admin" | "hr";
  is_active: boolean;
  date_joined: string;
}

export interface ApplicantAdmin {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
  application_count: number;
}

export interface AdminSummary {
  total_vacancies_open: number;
  total_vacancies_closed: number;
  total_applicants: number;
  total_applicants_pending_verification: number;
  total_hr_staff: number;
  total_applications: number;
}
