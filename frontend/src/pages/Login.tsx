import { useState } from "react";
import { Link } from "react-router-dom";
import { staffLogin, applicantLogin } from "../api/auth";
import { getStaffMe } from "../api/staff";

type Mode = "applicant" | "staff";

export default function Login() {
  const [mode, setMode] = useState<Mode>("applicant");
  const [identifier, setIdentifier] = useState(""); // email (applicant) or username (staff)
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "applicant") {
        await applicantLogin(identifier, password);
        // full reload so AuthContext re-initialises with the new token
        window.location.href = "/my/dashboard";
      } else {
        await staffLogin(identifier, password);
        // find out whether this is an Admin or HR account, route accordingly
        const me = await getStaffMe();
        window.location.href = me.role === "admin" ? "/admin/dashboard" : "/hr/dashboard";
      }
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        "Login failed. Check your credentials and try again.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden"
      style={{
        background:
          "linear-gradient(120deg, #eaf6ee 0%, #dcefe3 30%, #cfeadb 60%, #e7f4ec 100%)",
      }}
    >
      {/* Decorative blurred blobs behind the glass card */}
      <div
        className="absolute rounded-full blur-[90px] pointer-events-none"
        style={{ width: 520, height: 520, background: "#4EA72E", opacity: 0.22, top: -160, left: -140 }}
      />
      <div
        className="absolute rounded-full blur-[90px] pointer-events-none"
        style={{ width: 460, height: 460, background: "#2e7d32", opacity: 0.16, bottom: -160, right: -120 }}
      />
      <div
        className="absolute rounded-full blur-[90px] pointer-events-none"
        style={{ width: 300, height: 300, background: "#ffffff", opacity: 0.5, top: "55%", left: "60%" }}
      />

      {/* Glass card */}
      <div
        className="relative w-full max-w-sm rounded-[22px] border border-white/80 backdrop-blur-2xl px-10 py-11"
        style={{
          background: "rgba(255,255,255,0.55)",
          boxShadow: "0 30px 70px rgba(30,90,50,0.18)",
        }}
      >
        <h1 className="text-xl font-bold" style={{ color: "#123321" }}>
          NCC Recruitment Portal
        </h1>
        <p className="text-sm mt-1 mb-7" style={{ color: "#4a6b56" }}>
          Sign in to continue
        </p>

        <div className="flex mb-6 rounded-xl border border-white/90 bg-white/60 p-1">
          <button
            type="button"
            onClick={() => setMode("applicant")}
            className={`flex-1 py-2.5 text-sm font-bold rounded-lg transition ${
              mode === "applicant" ? "text-white" : ""
            }`}
            style={
              mode === "applicant"
                ? { background: "#4EA72E", boxShadow: "0 6px 16px rgba(78,167,46,0.4)" }
                : { color: "#4a6b56" }
            }
          >
            Applicant
          </button>
          <button
            type="button"
            onClick={() => setMode("staff")}
            className={`flex-1 py-2.5 text-sm font-bold rounded-lg transition ${
              mode === "staff" ? "text-white" : ""
            }`}
            style={
              mode === "staff"
                ? { background: "#4EA72E", boxShadow: "0 6px 16px rgba(78,167,46,0.4)" }
                : { color: "#4a6b56" }
            }
          >
            HR / Admin
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold mb-1.5" style={{ color: "#33553f" }}>
              {mode === "applicant" ? "Email" : "Username"}
            </label>
            <input
              type={mode === "applicant" ? "email" : "text"}
              required
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder={mode === "applicant" ? "you@example.com" : "username"}
              className="w-full rounded-[11px] border border-white/90 px-3.5 py-3 text-sm outline-none focus:ring-2 transition"
              style={{ background: "rgba(255,255,255,0.7)", color: "#16341f" }}
            />
          </div>
          <div>
            <label className="block text-xs font-bold mb-1.5" style={{ color: "#33553f" }}>
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-[11px] border border-white/90 px-3.5 py-3 text-sm outline-none focus:ring-2 transition"
              style={{ background: "rgba(255,255,255,0.7)", color: "#16341f" }}
            />
          </div>

          {error && (
            <p className="text-sm text-red-700 bg-red-50/80 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-[11px] py-3.5 text-sm font-bold text-white disabled:opacity-60 transition"
            style={{ background: "#4EA72E", boxShadow: "0 14px 28px rgba(78,167,46,0.35)" }}
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        {mode === "applicant" && (
          <p className="text-sm mt-5 text-center" style={{ color: "#4a6b56" }}>
            No account yet?{" "}
            <Link to="/register" className="font-bold" style={{ color: "#2e7d32" }}>
              Register
            </Link>
          </p>
        )}

        <p className="text-sm text-center mt-2">
          <Link to="/" className="hover:underline" style={{ color: "#6f8f7b" }}>
            Back to job listings
          </Link>
        </p>
      </div>
    </div>
  );
}
