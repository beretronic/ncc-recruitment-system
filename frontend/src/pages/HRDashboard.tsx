import { useEffect, useRef, useState } from "react";
import { Navbar } from "../components/Navbar";
import { JobFormModal } from "../components/JobFormModal";
import { JobApplicantsPanel } from "../components/JobApplicantsPanel";
import { ApplicationReviewModal } from "../components/ApplicationReviewModal";
import { useAuth } from "../context/AuthContext";
import { listJobs, createJob, updateJob, deleteJob } from "../api/jobs";
import { requestJobDeletion, apiErrorMessage } from "../api/deletionRequests";
import { DeleteRequestModal } from "../components/DeleteRequestModal";
import { getDashboardSummary, getApplication } from "../api/applications";
import type { Job, DashboardSummary, Application } from "../types";

// The API now also tells us whether a deletion request is awaiting Admin approval.
type JobRow = Job & { deletion_pending?: boolean };

export default function HRDashboard() {
  const { staffUser } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const [showForm, setShowForm] = useState(false);
  const [editingJob, setEditingJob] = useState<Job | null>(null);
  const [requestingJob, setRequestingJob] = useState<Job | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [reviewing, setReviewing] = useState<Application | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [showRejectedGlobal, setShowRejectedGlobal] = useState(false);

  // Refs for scroll-to-section behaviour when a stat card is clicked
  const funnelRef = useRef<HTMLDivElement | null>(null);
  const vacanciesRef = useRef<HTMLDivElement | null>(null);
  const leaderboardRef = useRef<HTMLDivElement | null>(null);

  function scrollTo(ref: React.RefObject<HTMLDivElement | null>) {
    ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function loadAll() {
    setLoading(true);
    Promise.all([listJobs(), getDashboardSummary()])
      .then(([j, s]) => {
        setJobs(j);
        setSummary(s);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadAll();
  }, []);

  async function handleCreateOrEdit(data: {
    title: string;
    description: string;
    requirements: string;
    location: string;
    deadline: string;
  }) {
    if (editingJob) {
      await updateJob(editingJob.id, data);
    } else {
      await createJob(data);
    }
    setShowForm(false);
    setEditingJob(null);
    loadAll();
  }

  async function handleToggleStatus(job: Job) {
    await updateJob(job.id, { status: job.status === "open" ? "closed" : "open" });
    loadAll();
  }

  async function handleDelete(job: Job) {
    const confirmed = window.confirm(
      `Delete the vacancy "${job.title}"?\n\n` +
        "This permanently removes the vacancy AND every application, interview and " +
        "status-history record linked to it. This cannot be undone.\n\n" +
        "If you only want to stop accepting applications, use Close instead."
    );
    if (!confirmed) return;
    try {
      await deleteJob(job.id);
      if (selectedJobId === job.id) setSelectedJobId(null);
      loadAll();
    } catch {
      window.alert("Could not delete this vacancy. Please try again.");
    }
  }

  // HR cannot delete directly: this files a request for an Admin to approve.
  async function handleRequestDeletion(reason: string) {
    if (!requestingJob) return;
    await requestJobDeletion(requestingJob.id, reason);
    setRequestingJob(null);
    loadAll();
  }

  async function openReview(applicationId: number) {
    setReviewLoading(true);
    try {
      const app = await getApplication(applicationId);
      setReviewing(app);
    } finally {
      setReviewLoading(false);
    }
  }


  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <div className="max-w-6xl mx-auto px-4 py-10">
        <h1 className="text-2xl font-semibold text-slate-900">HR Dashboard</h1>
        <p className="text-sm text-slate-500 mt-1 mb-6">
          Welcome, {staffUser?.first_name || staffUser?.username}. Manage vacancies and review
          applicants.
        </p>

        {loading ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : (
          <>
            {/* ---- Analytics summary (clickable, scrolls to relevant section) ---- */}
            {summary && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
                <StatCard
                  label="Total Applicants"
                  value={summary.total_applicants}
                  onClick={() => scrollTo(leaderboardRef)}
                />
                <StatCard
                  label="Open Vacancies"
                  value={summary.total_jobs_open}
                  onClick={() => scrollTo(vacanciesRef)}
                />
                <StatCard
                  label="Total Applications"
                  value={summary.total_applications}
                  onClick={() => scrollTo(leaderboardRef)}
                />
                <StatCard
                  label="Avg. Time to Hire"
                  value={
                    summary.avg_time_to_hire_days !== null
                      ? `${summary.avg_time_to_hire_days}d`
                      : "—"
                  }
                  onClick={() => scrollTo(funnelRef)}
                />
              </div>
            )}

            {summary && (
              <div ref={funnelRef} className="bg-white border border-slate-200 rounded-lg p-5 mb-8 scroll-mt-6">
                <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-3">
                  Status Funnel
                </h2>
                <div className="flex flex-wrap gap-4">
                  {Object.entries(summary.status_funnel).map(([status, count]) => (
                    <div key={status} className="text-center">
                      <div className="text-lg font-semibold text-slate-900">{count}</div>
                      <div className="text-xs text-slate-500">{status}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ---- Job management ---- */}
            <div ref={vacanciesRef} className="bg-white border border-slate-200 rounded-lg p-5 scroll-mt-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
                  Vacancies
                </h2>
                <button
                  onClick={() => {
                    setEditingJob(null);
                    setShowForm(true);
                  }}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-md px-4 py-2"
                >
                  + Post new vacancy
                </button>
              </div>

              {jobs.length === 0 ? (
                <p className="text-sm text-slate-500">No vacancies posted yet.</p>
              ) : (
                <div className="divide-y divide-slate-100">
                  {jobs.map((job) => (
                    <div key={job.id} className="py-3">
                      <div className="flex items-center justify-between">
                        <button
                          onClick={() =>
                            setSelectedJobId(selectedJobId === job.id ? null : job.id)
                          }
                          className="text-left flex-1"
                        >
                          <span className="font-medium text-slate-800">{job.title}</span>
                          <span
                            className={`ml-2 text-xs px-2 py-0.5 rounded-full ${
                              job.status === "open"
                                ? "bg-emerald-100 text-emerald-700"
                                : "bg-slate-100 text-slate-500"
                            }`}
                          >
                            {job.status}
                          </span>
                          <span className="text-xs text-slate-400 ml-2">
                            Closes {new Date(job.deadline).toLocaleDateString()}
                            {job.updated_by_name && (
                              <> · last edited by {job.updated_by_name}</>
                            )}
                          </span>
                        </button>
                        <div className="flex gap-3 text-xs">
                          <button
                            onClick={() => handleToggleStatus(job)}
                            className="text-slate-500 hover:underline"
                          >
                            {job.status === "open" ? "Close" : "Reopen"}
                          </button>
                          <button
                            onClick={() => {
                              setEditingJob(job);
                              setShowForm(true);
                            }}
                            className="text-slate-500 hover:underline"
                          >
                            Edit
                          </button>
                          {staffUser?.role === "admin" ? (
                            <button
                              onClick={() => handleDelete(job)}
                              className="text-red-500 hover:underline"
                            >
                              Delete
                            </button>
                          ) : (job as JobRow).deletion_pending ? (
                            <span className="text-amber-600">Deletion pending approval</span>
                          ) : (
                            <button
                              onClick={() => setRequestingJob(job)}
                              className="text-red-500 hover:underline"
                            >
                              Request deletion
                            </button>
                          )}
                        </div>
                      </div>

                      {selectedJobId === job.id && (
                        <JobApplicantsPanel jobId={job.id} jobTitle={job.title} />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* ---- Global leaderboard ---- */}
            {summary && summary.top_candidates_global.length > 0 && (() => {
              const rejectedGlobalCount = summary.top_candidates_global.filter(
                (c) => c.status === "Rejected"
              ).length;
              const visibleCandidates = showRejectedGlobal
                ? summary.top_candidates_global
                : summary.top_candidates_global.filter((c) => c.status !== "Rejected");

              return (
                <div ref={leaderboardRef} className="bg-white border border-slate-200 rounded-lg p-5 mt-8 scroll-mt-6">
                  <div className="flex items-start justify-between mb-1">
                    <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
                      Top Candidates (All Vacancies)
                    </h2>
                    {rejectedGlobalCount > 0 && (
                      <button
                        onClick={() => setShowRejectedGlobal((v) => !v)}
                        className="text-xs text-slate-400 hover:text-slate-600 hover:underline whitespace-nowrap"
                      >
                        {showRejectedGlobal ? "Hide" : "Show"} rejected ({rejectedGlobalCount})
                      </button>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 mb-3">
                    Click a candidate to open their CV and review.
                  </p>
                  {visibleCandidates.length === 0 ? (
                    <p className="text-sm text-slate-500">No candidates to show right now.</p>
                  ) : (
                    <table className="w-full text-sm">
                      <thead className="text-slate-500">
                        <tr>
                          <th className="text-left p-2">Applicant</th>
                          <th className="text-left p-2">Vacancy</th>
                          <th className="text-left p-2">Score</th>
                          <th className="text-left p-2">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {visibleCandidates.map((c) => (
                          <tr
                            key={c.application_id}
                            className="border-t border-slate-100 hover:bg-slate-50 cursor-pointer"
                            onClick={() => openReview(c.application_id)}
                          >
                            <td className="p-2 font-medium text-slate-800">{c.applicant_name}</td>
                            <td className="p-2 text-slate-600">{c.job_title}</td>
                            <td className="p-2">{c.fit_score}%</td>
                            <td className="p-2 text-slate-500">{c.status}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              );
            })()}
          </>
        )}
      </div>

      {showForm && (
        <JobFormModal
          initial={editingJob}
          onCancel={() => {
            setShowForm(false);
            setEditingJob(null);
          }}
          onSubmit={handleCreateOrEdit}
        />
      )}

      {requestingJob && (
        <DeleteRequestModal
          jobTitle={requestingJob.title}
          onCancel={() => setRequestingJob(null)}
          onSubmit={handleRequestDeletion}
          errorMessage={(err) => apiErrorMessage(err, "Could not send the request. Please try again.")}
        />
      )}

      {reviewLoading && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <p className="text-white text-sm">Loading application...</p>
        </div>
      )}

      {reviewing && (
        <ApplicationReviewModal
          application={reviewing}
          onClose={() => setReviewing(null)}
          onChanged={loadAll}
        />
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  onClick,
}: {
  label: string;
  value: string | number;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="text-left bg-white border border-slate-200 rounded-lg p-4 hover:border-emerald-400 hover:shadow-sm transition cursor-pointer"
    >
      <div className="text-2xl font-semibold text-slate-900">{value}</div>
      <div className="text-xs text-slate-500 mt-1">{label}</div>
    </button>
  );
}
