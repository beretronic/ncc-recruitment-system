import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../context/AuthContext";
import type { StoredRole } from "../api/client";

export function ProtectedRoute({
  children,
  allow,
  staffRole,
}: {
  children: ReactNode;
  allow: StoredRole[];
  staffRole?: "admin" | "hr"; // if set, requires this exact staff sub-role
}) {
  const { role, staffRole: currentStaffRole, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-500">
        Loading...
      </div>
    );
  }

  if (!role || !allow.includes(role)) {
    return <Navigate to="/login" replace />;
  }

  if (staffRole && currentStaffRole !== staffRole) {
    // logged in as staff, but wrong sub-role (e.g. HR hitting /admin/dashboard)
    const redirectTo = currentStaffRole === "admin" ? "/admin/dashboard" : "/hr/dashboard";
    return <Navigate to={redirectTo} replace />;
  }

  return <>{children}</>;
}
