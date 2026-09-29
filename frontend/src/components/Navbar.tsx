import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function Navbar() {
  const { role, staffRole, applicant, staffUser, logout } = useAuth();

  return (
    <nav className="border-b border-slate-200 bg-white">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link to="/" className="font-semibold text-slate-900">
          NCC Recruitment Portal
        </Link>

        <div className="flex items-center gap-4 text-sm">
          <Link to="/" className="text-slate-600 hover:text-emerald-600">
            Vacancies
          </Link>

          {role === "applicant" && (
            <>
              <Link to="/my/dashboard" className="text-slate-600 hover:text-emerald-600">
                My Applications
              </Link>
              <span className="text-slate-400">{applicant?.full_name}</span>
              <button onClick={logout} className="text-slate-600 hover:text-red-600">
                Logout
              </button>
            </>
          )}

          {role === "staff" && staffRole === "hr" && (
            <>
              <Link to="/hr/dashboard" className="text-slate-600 hover:text-emerald-600">
                HR Dashboard
              </Link>
              <span className="text-slate-400">{staffUser?.username}</span>
              <button onClick={logout} className="text-slate-600 hover:text-red-600">
                Logout
              </button>
            </>
          )}

          {role === "staff" && staffRole === "admin" && (
            <>
              <Link to="/admin/dashboard" className="text-slate-600 hover:text-emerald-600">
                Admin Dashboard
              </Link>
              <span className="text-slate-400">{staffUser?.username}</span>
              <button onClick={logout} className="text-slate-600 hover:text-red-600">
                Logout
              </button>
            </>
          )}

          {!role && (
            <>
              <Link to="/login" className="text-slate-600 hover:text-emerald-600">
                Login
              </Link>
              <Link
                to="/register"
                className="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-md"
              >
                Register
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
