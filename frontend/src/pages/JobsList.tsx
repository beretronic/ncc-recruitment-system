import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Navbar } from "../components/Navbar";
import { listJobs } from "../api/jobs";
import type { Job } from "../types";

export default function JobsList() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listJobs()
      .then(setJobs)
      .catch(() => setError("Could not load vacancies. Is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <div className="max-w-5xl mx-auto px-4 py-10">
        <h1 className="text-2xl font-semibold text-slate-900">Open Vacancies</h1>
        <p className="text-sm text-slate-500 mt-1 mb-8">
          Browse current opportunities at the National Competitiveness Commission.
        </p>

        {loading && <p className="text-slate-500 text-sm">Loading vacancies...</p>}

        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
            {error}
          </p>
        )}

        {!loading && !error && jobs.length === 0 && (
          <p className="text-slate-500 text-sm">
            No open vacancies right now. Check back later.
          </p>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {jobs.map((job) => (
            <Link
              key={job.id}
              to={`/jobs/${job.id}`}
              className="block bg-white border border-slate-200 rounded-lg p-5 hover:border-emerald-400 hover:shadow-sm transition"
            >
              <h2 className="font-semibold text-slate-900">{job.title}</h2>
              {job.location && (
                <p className="text-sm text-slate-500 mt-1">{job.location}</p>
              )}
              <p className="text-sm text-slate-600 mt-3 line-clamp-2">
                {job.description}
              </p>
              <p className="text-xs text-slate-400 mt-3">
                Closes {new Date(job.deadline).toLocaleDateString()}
              </p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
