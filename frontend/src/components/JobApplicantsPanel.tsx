import { useEffect, useState } from "react";
import { jobApplications, bulkUpdateStatus } from "../api/applications";
import { ApplicationReviewModal } from "./ApplicationReviewModal";
import type { Application, ApplicationStatus } from "../types";

const STATUSES: ApplicationStatus[] = [
  "Applied",
  "Shortlisted",
  "Interview",
  "Hired",
  "Rejected",
];

const STATUS_COLORS: Record<string, string> = {
  Applied: "bg-slate-100 text-slate-600",
  Shortlisted: "bg-blue-100 text-blue-700",
  Interview: "bg-amber-100 text-amber-700",
  Hired: "bg-emerald-100 text-emerald-700",
  Rejected: "bg-red-100 text-red-700",
};

export function JobApplicantsPanel({ jobId, jobTitle }: { jobId: number; jobTitle: string }) {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [bulkStatus, setBulkStatus] = useState<ApplicationStatus>("Shortlisted");
  const [busy, setBusy] = useState(false);
  const [reviewing, setReviewing] = useState<Application | null>(null);
  const [showRejected, setShowRejected] = useState(false);

  function load() {
    setLoading(true);
    jobApplications(jobId)
      .then(setApplications)
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
    setSelected(new Set());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleBulk() {
    if (selected.size === 0) return;
    setBusy(true);
    try {
      await bulkUpdateStatus(Array.from(selected), bulkStatus);
      setSelected(new Set());
      load();
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-slate-500 mt-4">Loading applicants...</p>;
  }

  const rejectedCount = applications.filter((a) => a.status === "Rejected").length;
  const visibleApplications = showRejected
    ? applications
    : applications.filter((a) => a.status !== "Rejected");

  return (
    <div className="mt-4">
      <div className="flex items-start justify-between mb-1">
        <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
          Applicants for "{jobTitle}" (ranked by CV match score)
        </h3>
        {rejectedCount > 0 && (
          <button
            onClick={() => setShowRejected((v) => !v)}
            className="text-xs text-slate-400 hover:text-slate-600 hover:underline whitespace-nowrap"
          >
            {showRejected ? "Hide" : "Show"} rejected ({rejectedCount})
          </button>
        )}
      </div>
      <p className="text-xs text-slate-400 mb-3">
        Click an applicant to open their CV and choose a next step.
      </p>

      {visibleApplications.length === 0 ? (
        <p className="text-sm text-slate-500">
          {applications.length === 0
            ? "No applications yet for this vacancy."
            : "No applicants to review right now — all applications for this vacancy have been rejected."}
        </p>
      ) : (
        <>
          <div className="flex items-center gap-3 mb-3 bg-slate-50 border border-slate-200 rounded-md p-3">
            <span className="text-sm text-slate-600">{selected.size} selected</span>
            <select
              value={bulkStatus}
              onChange={(e) => setBulkStatus(e.target.value as ApplicationStatus)}
              className="text-sm border border-slate-300 rounded-md px-2 py-1"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <button
              onClick={handleBulk}
              disabled={selected.size === 0 || busy}
              className="text-sm bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-medium rounded-md px-3 py-1.5"
            >
              Bulk apply to selected
            </button>
            <span className="text-xs text-slate-400 ml-auto">
              For individual decisions, click an applicant to review their CV first.
            </span>
          </div>

          <div className="overflow-x-auto border border-slate-200 rounded-md">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="p-2 w-8"></th>
                  <th className="text-left p-2">Applicant</th>
                  <th className="text-left p-2">Match Score</th>
                  <th className="text-left p-2">Status</th>
                  <th className="text-left p-2">Applied</th>
                </tr>
              </thead>
              <tbody>
                {visibleApplications.map((app) => (
                  <tr
                    key={app.id}
                    className="border-t border-slate-100 hover:bg-slate-50 cursor-pointer"
                    onClick={() => setReviewing(app)}
                  >
                    <td className="p-2" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selected.has(app.id)}
                        onChange={() => toggleSelect(app.id)}
                      />
                    </td>
                    <td className="p-2 font-medium text-slate-800">{app.applicant_name}</td>
                    <td className="p-2">
                      {app.fit_score !== null ? `${app.fit_score}%` : "—"}
                    </td>
                    <td className="p-2">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          STATUS_COLORS[app.status] || "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {app.status}
                      </span>
                    </td>
                    <td className="p-2 text-slate-500">
                      {new Date(app.applied_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {reviewing && (
        <ApplicationReviewModal
          application={reviewing}
          onClose={() => setReviewing(null)}
          onChanged={load}
        />
      )}
    </div>
  );
}
