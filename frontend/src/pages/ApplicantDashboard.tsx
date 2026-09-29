import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Navbar } from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import { myApplications, getRecommendations } from "../api/applications";
import type { Application, JobRecommendation } from "../types";

const STATUS_COLORS: Record<string, string> = {
  Applied: "bg-slate-100 text-slate-600",
  Shortlisted: "bg-blue-100 text-blue-700",
  Interview: "bg-amber-100 text-amber-700",
  Hired: "bg-emerald-100 text-emerald-700",
  Rejected: "bg-red-100 text-red-700",
};

export default function ApplicantDashboard() {
  const { applicant } = useAuth();
  const [applications, setApplications] = useState<Application[]>([]);
  const [recommendations, setRecommendations] = useState<JobRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [recError, setRecError] = useState<string | null>(null);

  useEffect(() => {
    myApplications()
      .then(setApplications)
      .finally(() => setLoading(false));

    getRecommendations()
      .then(setRecommendations)
      .catch((err) => {
        setRecError(
          err?.response?.data?.detail ||
            "Recommendations will appear once you've applied to at least one vacancy."
        );
      });
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 py-10">
        <h1 className="text-2xl font-semibold text-slate-900">
          Welcome, {applicant?.full_name || "..."}
        </h1>
        <p className="text-sm text-slate-500 mt-1 mb-8">
          Track your applications and see vacancies matched to your CV.
        </p>

        {/* ---- My Applications ---- */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 mb-8">
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-4">
            My Applications
          </h2>

          {loading ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : applications.length === 0 ? (
            <p className="text-sm text-slate-500">
              You haven't applied to any vacancies yet.{" "}
              <Link to="/" className="text-emerald-600 hover:underline">
                Browse open vacancies
              </Link>
              .
            </p>
          ) : (
            <div className="divide-y divide-slate-100">
              {applications.map((app) => (
                <div key={app.id} className="py-3 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-slate-800">{app.job_title}</p>
                    <p className="text-xs text-slate-400">
                      Applied {new Date(app.applied_at).toLocaleDateString()}
                      {app.fit_score !== null && ` · Match score: ${app.fit_score}%`}
                    </p>
                  </div>
                  <div className="text-right">
                    <span
                      className={`text-xs font-medium px-3 py-1 rounded-full inline-block ${
                        STATUS_COLORS[app.status] || "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {app.status}
                    </span>
                    {app.status === "Interview" && app.interview_date && (
                      <p className="text-xs text-slate-500 mt-1">
                        {new Date(app.interview_date).toLocaleString(undefined, {
                          dateStyle: "medium",
                          timeStyle: "short",
                        })}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ---- Recommendations ---- */}
        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-4">
            Recommended For You
          </h2>

          {recError && !recommendations.length ? (
            <p className="text-sm text-slate-500">{recError}</p>
          ) : recommendations.length === 0 ? (
            <p className="text-sm text-slate-500">No recommendations available right now.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {recommendations.map((rec) => (
                <Link
                  key={rec.job.id}
                  to={`/jobs/${rec.job.id}`}
                  className="block border border-slate-200 rounded-lg p-4 hover:border-emerald-400 hover:shadow-sm transition"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium text-slate-800">{rec.job.title}</h3>
                    <span className="text-xs font-medium bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full">
                      {rec.match_score}% match
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">{rec.job.location}</p>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
