import { useEffect, useState } from "react";
import {
  listDeletionRequests,
  approveDeletionRequest,
  rejectDeletionRequest,
  apiErrorMessage,
} from "../api/deletionRequests";
import type { DeletionRequest } from "../api/deletionRequests";

export function DeletionRequestsPanel() {
  const [requests, setRequests] = useState<DeletionRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  function load() {
    listDeletionRequests()
      .then(setRequests)
      .catch(() => setError("Could not load deletion requests."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  async function decide(req: DeletionRequest, approve: boolean) {
    if (approve) {
      const ok = window.confirm(
        `Approve deletion of "${req.job_title}"?\n\n` +
          `This permanently deletes the vacancy and its ${req.application_count} application(s), ` +
          "along with all interviews and status history. This cannot be undone."
      );
      if (!ok) return;
    }
    setBusyId(req.id);
    setError(null);
    try {
      if (approve) await approveDeletionRequest(req.id);
      else await rejectDeletionRequest(req.id);
      load();
    } catch (err) {
      setError(apiErrorMessage(err, "Could not complete that action. Please try again."));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 mb-8">
      <div className="flex items-center gap-2 mb-3">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
          Vacancy deletion requests
        </h2>
        {requests.length > 0 && (
          <span className="text-xs font-medium bg-amber-100 text-amber-700 rounded-full px-2 py-0.5">
            {requests.length} pending
          </span>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2 mb-3">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : requests.length === 0 ? (
        <p className="text-sm text-slate-500">No pending requests.</p>
      ) : (
        <div className="divide-y divide-slate-100">
          {requests.map((req) => (
            <div key={req.id} className="py-3 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
              <div>
                <div className="font-medium text-slate-900">{req.job_title}</div>
                <div className="text-xs text-slate-500 mt-0.5">
                  Requested by {req.requested_by_name || "unknown"} on{" "}
                  {new Date(req.requested_at).toLocaleString()}
                </div>
                <div className="text-sm text-slate-700 mt-2">
                  <span className="text-slate-500">Reason: </span>
                  {req.reason}
                </div>
                <div className="text-xs text-amber-700 mt-1">
                  Approving also permanently deletes {req.application_count} application(s).
                </div>
              </div>
              <div className="flex gap-2 shrink-0">
                <button
                  disabled={busyId === req.id}
                  onClick={() => decide(req, true)}
                  className="text-xs px-3 py-1.5 rounded-md bg-red-600 text-white disabled:opacity-60"
                >
                  Approve &amp; delete
                </button>
                <button
                  disabled={busyId === req.id}
                  onClick={() => decide(req, false)}
                  className="text-xs px-3 py-1.5 rounded-md border border-slate-300 text-slate-600 disabled:opacity-60"
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
