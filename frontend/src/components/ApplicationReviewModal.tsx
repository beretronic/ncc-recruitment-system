import { useEffect, useState } from "react";
import { api } from "../api/client";
import {
  updateApplicationStatus,
  getAuditLog,
  scheduleInterview,
} from "../api/applications";
import type { Application, ApplicationStatus, StatusAuditLogEntry } from "../types";

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

export function ApplicationReviewModal({
  application,
  onClose,
  onChanged,
}: {
  application: Application;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [current, setCurrent] = useState(application);
  // The CV is fetched with the login token and shown from a local blob URL. It is
  // not served from a public address, so it stays private and works regardless of
  // browser iframe restrictions.
  const [cvUrl, setCvUrl] = useState<string | null>(null);
  const [cvError, setCvError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [auditEntries, setAuditEntries] = useState<StatusAuditLogEntry[]>([]);
  const [showInterviewForm, setShowInterviewForm] = useState(false);
  const [interviewDate, setInterviewDate] = useState("");
  const [interviewNotes, setInterviewNotes] = useState("");

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    setCvUrl(null);
    setCvError(false);
    api
      .get(`/applications/${current.id}/cv/`, { responseType: "blob" })
      .then((res) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(res.data);
        setCvUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setCvError(true);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [current.id]);

  useEffect(() => {
    getAuditLog(application.id).then(setAuditEntries);
  }, [application.id]);

  async function setStatus(status: ApplicationStatus) {
    setBusy(true);
    try {
      const updated = await updateApplicationStatus(current.id, status);
      setCurrent(updated);
      const entries = await getAuditLog(current.id);
      setAuditEntries(entries);
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function submitInterview() {
    if (!interviewDate) return;
    setBusy(true);
    try {
      await scheduleInterview(current.id, new Date(interviewDate).toISOString(), interviewNotes);
      setCurrent({ ...current, status: "Interview" });
      const entries = await getAuditLog(current.id);
      setAuditEntries(entries);
      setShowInterviewForm(false);
      setInterviewDate("");
      setInterviewNotes("");
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          {/* ---- Header ---- */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">
                {current.applicant_name}
              </h2>
              <p className="text-sm text-slate-500">
                Applying for {current.job_title} · Match score:{" "}
                <strong>{current.fit_score !== null ? `${current.fit_score}%` : "—"}</strong>
              </p>
            </div>
            <span
              className={`text-xs font-medium px-3 py-1 rounded-full ${
                STATUS_COLORS[current.status] || "bg-slate-100 text-slate-600"
              }`}
            >
              {current.status}
            </span>
          </div>

          {/* ---- CV preview ---- */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
                CV
              </h3>
              {cvUrl && (
                <a
                  href={cvUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-emerald-600 hover:underline"
                >
                  Open in new tab
                </a>
              )}
            </div>
            {cvError ? (
              <div className="w-full h-40 border border-slate-200 rounded-md bg-slate-50 flex items-center justify-center text-sm text-slate-500 px-4 text-center">
                This CV file is no longer available.
              </div>
            ) : !cvUrl ? (
              <div className="w-full h-40 border border-slate-200 rounded-md bg-slate-50 flex items-center justify-center text-sm text-slate-500">
                Loading CV...
              </div>
            ) : (
              <iframe
                src={cvUrl}
                title="CV preview"
                className="w-full h-96 border border-slate-200 rounded-md"
              />
            )}
          </div>

          {/* ---- Actions - only shown after the CV is visible above ---- */}
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-2">
              Actions
            </h3>
            <div className="flex flex-wrap gap-2">
              {STATUSES.filter((s) => s !== current.status).map((s) => (
                <button
                  key={s}
                  disabled={busy}
                  onClick={() => setStatus(s)}
                  className="text-sm border border-slate-300 hover:border-emerald-400 hover:text-emerald-700 rounded-md px-3 py-1.5 disabled:opacity-50"
                >
                  Move to {s}
                </button>
              ))}
              <button
                disabled={busy}
                onClick={() => setShowInterviewForm(true)}
                className="text-sm bg-emerald-600 hover:bg-emerald-700 text-white rounded-md px-3 py-1.5 disabled:opacity-50"
              >
                Schedule Interview
              </button>
            </div>
          </div>

          {showInterviewForm && (
            <div className="mb-4 border border-slate-200 rounded-md p-4 bg-slate-50">
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Interview date & time
              </label>
              <input
                type="datetime-local"
                value={interviewDate}
                onChange={(e) => setInterviewDate(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm mb-3"
              />
              <label className="block text-sm font-medium text-slate-700 mb-1">Notes</label>
              <textarea
                rows={2}
                value={interviewNotes}
                onChange={(e) => setInterviewNotes(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm mb-3"
              />
              <div className="flex gap-2">
                <button
                  onClick={submitInterview}
                  disabled={!interviewDate || busy}
                  className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white text-sm font-medium rounded-md px-4 py-1.5"
                >
                  Confirm
                </button>
                <button
                  onClick={() => setShowInterviewForm(false)}
                  className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-md px-4 py-1.5"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* ---- Audit log ---- */}
          <div>
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-2">
              Status History
            </h3>
            {auditEntries.length === 0 ? (
              <p className="text-sm text-slate-500">No history yet.</p>
            ) : (
              <ul className="space-y-1 text-sm">
                {auditEntries.map((entry) => (
                  <li key={entry.id} className="text-slate-600">
                    {entry.old_status || "(new)"} → <strong>{entry.new_status}</strong>
                    <span className="text-xs text-slate-400 ml-2">
                      {new Date(entry.timestamp).toLocaleString()}
                      {entry.changed_by_name ? ` · by ${entry.changed_by_name}` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <button
            onClick={onClose}
            className="mt-6 w-full bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-md py-2 text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
