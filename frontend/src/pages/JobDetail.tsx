import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Navbar } from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import { getJob } from "../api/jobs";
import { submitApplication } from "../api/applications";
import type { Job } from "../types";

export default function JobDetail() {
  const { id } = useParams();
  const { role } = useAuth();

  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const [cvFile, setCvFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applySuccess, setApplySuccess] = useState<number | null>(null); // fit_score

  useEffect(() => {
    if (!id) return;
    getJob(Number(id))
      .then(setJob)
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleApply(e: React.FormEvent) {
    e.preventDefault();
    if (!cvFile || !job) return;
    setApplyError(null);
    setSubmitting(true);
    try {
      const application = await submitApplication(job.id, cvFile);
      setApplySuccess(application.fit_score);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const cvFileError = err?.response?.data?.cv_file?.[0];
      setApplyError(detail || cvFileError || "Could not submit your application. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50">
        <Navbar />
        <div className="max-w-3xl mx-auto px-4 py-10 text-slate-500 text-sm">
          Loading...
        </div>
      </div>
    );
  }

  if (notFound || !job) {
    return (
      <div className="min-h-screen bg-slate-50">
        <Navbar />
        <div className="max-w-3xl mx-auto px-4 py-10">
          <p className="text-slate-500 text-sm">
            This vacancy could not be found, or is no longer open.
          </p>
          <Link to="/" className="text-emerald-600 text-sm hover:underline mt-2 inline-block">
            Back to vacancies
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <div className="max-w-3xl mx-auto px-4 py-10">
        <Link to="/" className="text-sm text-slate-400 hover:underline">
          ← Back to vacancies
        </Link>

        <div className="bg-white border border-slate-200 rounded-lg p-6 mt-4">
          <h1 className="text-2xl font-semibold text-slate-900">{job.title}</h1>
          <p className="text-sm text-slate-500 mt-1">
            {job.location} · Closes {new Date(job.deadline).toLocaleDateString()}
          </p>

          <div className="mt-6">
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
              Description
            </h2>
            <p className="text-sm text-slate-600 mt-2 whitespace-pre-line">
              {job.description}
            </p>
          </div>

          <div className="mt-6">
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
              Requirements
            </h2>
            <p className="text-sm text-slate-600 mt-2 whitespace-pre-line">
              {job.requirements}
            </p>
          </div>
        </div>

        {/* ---- Apply section ---- */}
        <div className="bg-white border border-slate-200 rounded-lg p-6 mt-6">
          {applySuccess !== null ? (
            <div className="text-center py-4">
              <p className="text-emerald-700 font-medium">
                Application submitted successfully!
              </p>
              <p className="text-sm text-slate-500 mt-2">
                Your CV match score for this role: {applySuccess}%
              </p>
              <Link
                to="/my/dashboard"
                className="inline-block mt-4 text-emerald-600 text-sm font-medium hover:underline"
              >
                View my applications
              </Link>
            </div>
          ) : role === "applicant" ? (
            <form onSubmit={handleApply}>
              <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-3">
                Apply for this vacancy
              </h2>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Upload your CV (PDF only)
              </label>
              <input
                type="file"
                accept="application/pdf"
                required
                onChange={(e) => setCvFile(e.target.files?.[0] || null)}
                className="w-full text-sm border border-slate-300 rounded-md px-3 py-2 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:bg-emerald-50 file:text-emerald-700 file:font-medium"
              />

              {applyError && (
                <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2 mt-3">
                  {applyError}
                </p>
              )}

              <button
                type="submit"
                disabled={submitting || !cvFile}
                className="mt-4 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white font-medium rounded-md py-2 px-5 text-sm transition"
              >
                {submitting ? "Submitting..." : "Submit application"}
              </button>
            </form>
          ) : role === "staff" ? (
            <p className="text-sm text-slate-500">
              You're signed in as HR/Admin. Applicants apply from their own accounts.
            </p>
          ) : (
            <div className="text-center py-2">
              <p className="text-sm text-slate-600 mb-3">
                Sign in as an applicant to apply for this vacancy.
              </p>
              <Link
                to="/login"
                className="inline-block bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-md py-2 px-5 text-sm transition"
              >
                Login / Register
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
