import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getActiveRole, clearTokens, type StoredRole } from "../api/client";
import { getApplicantMe } from "../api/auth";
import { getStaffMe } from "../api/staff";
import type { Applicant, StaffMember } from "../types";

interface AuthContextValue {
  role: StoredRole; // "staff" (admin/hr) | "applicant" | null
  staffRole: "admin" | "hr" | null; // the ACTUAL staff role, once known
  staffUser: StaffMember | null;
  applicant: Applicant | null;
  loading: boolean;
  logout: () => void;
  refreshApplicant: () => Promise<void>;
  refreshStaff: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<StoredRole>(getActiveRole());
  const [applicant, setApplicant] = useState<Applicant | null>(null);
  const [staffUser, setStaffUser] = useState<StaffMember | null>(null);
  const [loading, setLoading] = useState(true);

  async function refreshApplicant() {
    if (getActiveRole() === "applicant") {
      try {
        const me = await getApplicantMe();
        setApplicant(me);
      } catch {
        setApplicant(null);
      }
    }
  }

  async function refreshStaff() {
    if (getActiveRole() === "staff") {
      try {
        const me = await getStaffMe();
        setStaffUser(me);
      } catch {
        setStaffUser(null);
      }
    }
  }

  useEffect(() => {
    const currentRole = getActiveRole();
    setRole(currentRole);
    if (currentRole === "applicant") {
      refreshApplicant().finally(() => setLoading(false));
    } else if (currentRole === "staff") {
      refreshStaff().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function logout() {
    clearTokens();
    setRole(null);
    setApplicant(null);
    setStaffUser(null);
    window.location.href = "/login";
  }

  return (
    <AuthContext.Provider
      value={{
        role,
        staffRole: staffUser?.role || null,
        staffUser,
        applicant,
        loading,
        logout,
        refreshApplicant,
        refreshStaff,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
