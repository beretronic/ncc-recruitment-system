import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

export const api = axios.create({
  baseURL: API_BASE_URL,
});

// ---- Token storage helpers ----
// HR/Admin and Applicant use separate token pairs (different auth systems on
// the backend), so we keep them under separate localStorage keys and track
// which role is "active" in this browser session.

export type StoredRole = "staff" | "applicant" | null; // "staff" covers admin+hr (same JWT system)

export function getActiveRole(): StoredRole {
  return (localStorage.getItem("active_role") as StoredRole) || null;
}

export function setActiveRole(role: StoredRole) {
  if (role) localStorage.setItem("active_role", role);
  else localStorage.removeItem("active_role");
}

export function setStaffTokens(access: string, refresh: string) {
  localStorage.setItem("staff_access", access);
  localStorage.setItem("staff_refresh", refresh);
  setActiveRole("staff");
}

export function setApplicantTokens(access: string, refresh: string) {
  localStorage.setItem("applicant_access", access);
  localStorage.setItem("applicant_refresh", refresh);
  setActiveRole("applicant");
}

export function clearTokens() {
  localStorage.removeItem("staff_access");
  localStorage.removeItem("staff_refresh");
  localStorage.removeItem("applicant_access");
  localStorage.removeItem("applicant_refresh");
  setActiveRole(null);
}

function getAccessToken(): string | null {
  const role = getActiveRole();
  if (role === "staff") return localStorage.getItem("staff_access");
  if (role === "applicant") return localStorage.getItem("applicant_access");
  return null;
}

function getRefreshToken(): string | null {
  const role = getActiveRole();
  if (role === "staff") return localStorage.getItem("staff_refresh");
  if (role === "applicant") return localStorage.getItem("applicant_refresh");
  return null;
}

// Attach the active token to every request automatically
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On a 401, try refreshing the token once, then retry the original request.
// HR/Admin uses the standard /api/token/refresh/ endpoint. Applicants don't
// currently have a refresh endpoint on the backend, so for now an expired
// applicant token just logs them out - can be added to the backend later.
let isRefreshing = false;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      const role = getActiveRole();

      if (role === "staff" && !isRefreshing) {
        originalRequest._retry = true;
        isRefreshing = true;
        try {
          const refresh = getRefreshToken();
          const res = await axios.post(`${API_BASE_URL}/token/refresh/`, { refresh });
          setStaffTokens(res.data.access, refresh as string);
          isRefreshing = false;
          originalRequest.headers.Authorization = `Bearer ${res.data.access}`;
          return api(originalRequest);
        } catch (refreshError) {
          isRefreshing = false;
          clearTokens();
          window.location.href = "/login";
          return Promise.reject(refreshError);
        }
      } else if (role === "applicant") {
        clearTokens();
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
