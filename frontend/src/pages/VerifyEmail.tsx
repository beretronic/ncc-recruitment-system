import { useState } from "react";
import { Link } from "react-router-dom";
import { applicantVerify } from "../api/auth";

const glassBg = {
  background:
    "linear-gradient(120deg, #eaf6ee 0%, #dcefe3 30%, #cfeadb 60%, #e7f4ec 100%)",
};

function Blobs() {
  return (
    <>
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
    </>
  );
}

export default function VerifyEmail() {
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await applicantVerify(token.trim());
      setSuccess(true);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Invalid or expired token.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden" style={glassBg}>
      <Blobs />
      <div
        className="relative w-full max-w-sm rounded-[22px] border border-white/80 backdrop-blur-2xl px-10 py-11"
        style={{ background: "rgba(255,255,255,0.55)", boxShadow: "0 30px 70px rgba(30,90,50,0.18)" }}
      >
        <h1 className="text-xl font-bold" style={{ color: "#123321" }}>
          Verify your account
        </h1>

        {success ? (
          <>
            <p className="text-sm mt-4 mb-7" style={{ color: "#4a6b56" }}>
              Your account has been verified. You can now sign in.
            </p>
            <Link
              to="/login"
              className="inline-block w-full text-center rounded-[11px] py-3.5 text-sm font-bold text-white transition"
              style={{ background: "#4EA72E", boxShadow: "0 14px 28px rgba(78,167,46,0.35)" }}
            >
              Go to login
            </Link>
          </>
        ) : (
          <>
            <p className="text-sm mt-1 mb-7" style={{ color: "#4a6b56" }}>
              Paste the verification token from your confirmation email
              below.
            </p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold mb-1.5" style={{ color: "#33553f" }}>
                  Verification token
                </label>
                <input
                  required
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
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
                {loading ? "Verifying..." : "Verify account"}
              </button>
            </form>
          </>
        )}

        <p className="text-sm text-center mt-5">
          <Link to="/login" className="hover:underline" style={{ color: "#6f8f7b" }}>
            Back to login
          </Link>
        </p>
      </div>
    </div>
  );
}
