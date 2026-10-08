import { useState } from "react";

interface Props {
  jobTitle: string;
  onCancel: () => void;
  onSubmit: (reason: string) => Promise<void>;
  errorMessage: (err: unknown) => string;
}

export function DeleteRequestModal({ jobTitle, onCancel, onSubmit, errorMessage }: Props) {
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await onSubmit(reason);
    } catch (err) {
      setError(errorMessage(err));
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-lg">
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <h2 className="text-lg font-semibold text-slate-900">Request deletion</h2>
          <p className="text-sm text-slate-600">
            Vacancy: <span className="font-medium text-slate-900">{jobTitle}</span>
          </p>
          <p className="text-xs text-slate-500">
            Nothing is deleted yet. An Admin will review this request. If approved, the vacancy
            and every application, interview and status-history record linked to it are
            permanently removed. If you only want to stop accepting applications, use Close instead.
          </p>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Reason for deletion <span className="text-red-500">*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              required
              placeholder="e.g. Posted by mistake / duplicate of another vacancy"
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
              {error}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onCancel}
              className="text-sm px-4 py-2 rounded-md border border-slate-300 text-slate-600"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="text-sm px-4 py-2 rounded-md bg-red-600 text-white disabled:opacity-60"
            >
              {saving ? "Sending..." : "Send request to Admin"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
