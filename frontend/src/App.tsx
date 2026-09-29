import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";

import Login from "./pages/Login";
import Register from "./pages/Register";
import VerifyEmail from "./pages/VerifyEmail";
import JobsList from "./pages/JobsList";
import JobDetail from "./pages/JobDetail";
import ApplicantDashboard from "./pages/ApplicantDashboard";
import HRDashboard from "./pages/HRDashboard";
import AdminDashboard from "./pages/AdminDashboard";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public */}
          <Route path="/" element={<JobsList />} />
          <Route path="/jobs/:id" element={<JobDetail />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify" element={<VerifyEmail />} />

          {/* Applicant only */}
          <Route
            path="/my/dashboard"
            element={
              <ProtectedRoute allow={["applicant"]}>
                <ApplicantDashboard />
              </ProtectedRoute>
            }
          />

          {/* HR only (Admin is redirected to /admin/dashboard instead) */}
          <Route
            path="/hr/dashboard"
            element={
              <ProtectedRoute allow={["staff"]} staffRole="hr">
                <HRDashboard />
              </ProtectedRoute>
            }
          />

          {/* Admin only (HR is redirected to /hr/dashboard instead) */}
          <Route
            path="/admin/dashboard"
            element={
              <ProtectedRoute allow={["staff"]} staffRole="admin">
                <AdminDashboard />
              </ProtectedRoute>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
