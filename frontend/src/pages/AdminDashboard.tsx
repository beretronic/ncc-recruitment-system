import { useEffect, useState } from "react";
import { Navbar } from "../components/Navbar";
import { StaffFormModal } from "../components/StaffFormModal";
import { DeletionRequestsPanel } from "../components/DeletionRequestsPanel";
import { useAuth } from "../context/AuthContext";
import {
  getAdminSummary,
  listStaff,
  createStaff,
  updateStaff,
  listApplicantsAdmin,
  updateApplicantAdmin,
} from "../api/staff";
import type { AdminSummary, StaffMember, ApplicantAdmin } from "../types";

export default function AdminDashboard() {
  const { staffUser } = useAuth();
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [applicants, setApplicants] = useState<ApplicantAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [showStaffForm, setShowStaffForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"staff" | "applicants">("staff");

  function loadAll() {
    setLoading(true);
    Promise.all([getAdminSummary(), listStaff(), listApplicantsAdmin()])
      .then(([s, st, ap]) => {
        setSummary(s);
        setStaff(st);
        setApplicants(ap);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadAll();
  }, []);

  async function handleCreateStaff(data: Parameters<typeof createStaff>[0]) {
    await createStaff(data);
    setShowStaffForm(false);
    loadAll();
  }

  async function handleToggleStaff(member: StaffMember) {
    setError(null);
    try {
      await updateStaff(member.id, { is_active: !member.is_active });
      loadAll();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Could not update this account.");
    }
  }

  async function handleToggleApplicant(applicant: ApplicantAdmin) {
    await updateApplicantAdmin(applicant.id, { is_active: !applicant.is_active });
    loadAll();
  }

  async function handleForceVerify(applicant: ApplicantAdmin) {
    await updateApplicantAdmin(applicant.id, { is_verified: true });
    loadAll();
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <div className="max-w-5xl mx-auto px-4 py-10">
        <h1 className="text-2xl font-semibold text-slate-900">Admin Dashboard</h1>
        <p className="text-sm text-slate-500 mt-1 mb-8">
          Welcome, {staffUser?.first_name || staffUser?.username}. Account and vacancy oversight
          for the National Competitiveness Commission recruitment platform.
        </p>

        {loading ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : (
          <>
            {/* ---- Lightweight summary (no matching-score detail, deliberately) ---- */}
            {summary && (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8">
                <StatCard label="Open Vacancies" value={summary.total_vacancies_open} />
                <StatCard label="Closed Vacancies" value={summary.total_vacancies_closed} />
                <StatCard label="Total Applicants" value={summary.total_applicants} />
                <StatCard
                  label="Pending Verification"
                  value={summary.total_applicants_pending_verification}
                />
                <StatCard label="HR Staff" value={summary.total_hr_staff} />
                <StatCard label="Total Applications" value={summary.total_applications} />
              </div>
            )}

            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2 mb-4">
                {error}
              </p>
            )}

            <DeletionRequestsPanel />

            {/* ---- Tabs ---- */}
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setTab("staff")}
                className={`text-sm font-medium px-4 py-2 rounded-md ${
                  tab === "staff" ? "bg-emerald-600 text-white" : "bg-white border border-slate-200 text-slate-600"
                }`}
              >
                HR / Admin Accounts
              </button>
              <button
                onClick={() => setTab("applicants")}
                className={`text-sm font-medium px-4 py-2 rounded-md ${
                  tab === "applicants" ? "bg-emerald-600 text-white" : "bg-white border border-slate-200 text-slate-600"
                }`}
              >
                Applicant Accounts
              </button>
            </div>

            {/* ---- Staff management ---- */}
            {tab === "staff" && (
              <div className="bg-white border border-slate-200 rounded-lg p-5">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
                    HR / Admin Accounts
                  </h2>
                  <button
                    onClick={() => setShowStaffForm(true)}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-md px-4 py-2"
                  >
                    + Add account
                  </button>
                </div>
                <table className="w-full text-sm">
                  <thead className="text-slate-500">
                    <tr>
                      <th className="text-left p-2">Username</th>
                      <th className="text-left p-2">Email</th>
                      <th className="text-left p-2">Role</th>
                      <th className="text-left p-2">Status</th>
                      <th className="text-left p-2">Joined</th>
                      <th className="text-left p-2">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {staff.map((s) => (
                      <tr key={s.id} className="border-t border-slate-100">
                        <td className="p-2 font-medium text-slate-800">{s.username}</td>
                        <td className="p-2 text-slate-600">{s.email}</td>
                        <td className="p-2 capitalize text-slate-600">{s.role}</td>
                        <td className="p-2">
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full ${
                              s.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                            }`}
                          >
                            {s.is_active ? "Active" : "Suspended"}
                          </span>
                        </td>
                        <td className="p-2 text-slate-400">
                          {new Date(s.date_joined).toLocaleDateString()}
                        </td>
                        <td className="p-2">
                          <button
                            onClick={() => handleToggleStaff(s)}
                            className={`text-xs hover:underline ${s.is_active ? "text-red-500" : "text-emerald-600"}`}
                          >
                            {s.is_active ? "Suspend" : "Reactivate"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* ---- Applicant account management ---- */}
            {tab === "applicants" && (
              <div className="bg-white border border-slate-200 rounded-lg p-5">
                <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-4">
                  Applicant Accounts
                </h2>
                <table className="w-full text-sm">
                  <thead className="text-slate-500">
                    <tr>
                      <th className="text-left p-2">Name</th>
                      <th className="text-left p-2">Email</th>
                      <th className="text-left p-2">Verified</th>
                      <th className="text-left p-2">Status</th>
                      <th className="text-left p-2">Applications</th>
                      <th className="text-left p-2">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {applicants.map((a) => (
                      <tr key={a.id} className="border-t border-slate-100">
                        <td className="p-2 font-medium text-slate-800">{a.full_name}</td>
                        <td className="p-2 text-slate-600">{a.email}</td>
                        <td className="p-2">
                          {a.is_verified ? (
                            <span className="text-xs text-emerald-600">Verified</span>
                          ) : (
                            <span className="text-xs text-amber-600">Pending</span>
                          )}
                        </td>
                        <td className="p-2">
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full ${
                              a.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                            }`}
                          >
                            {a.is_active ? "Active" : "Suspended"}
                          </span>
                        </td>
                        <td className="p-2 text-slate-500">{a.application_count}</td>
                        <td className="p-2 space-x-2 whitespace-nowrap">
                          {!a.is_verified && (
                            <button
                              onClick={() => handleForceVerify(a)}
                              className="text-xs text-emerald-600 hover:underline"
                            >
                              Verify
                            </button>
                          )}
                          <button
                            onClick={() => handleToggleApplicant(a)}
                            className={`text-xs hover:underline ${a.is_active ? "text-red-500" : "text-emerald-600"}`}
                          >
                            {a.is_active ? "Suspend" : "Reactivate"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>

      {showStaffForm && (
        <StaffFormModal onCancel={() => setShowStaffForm(false)} onSubmit={handleCreateStaff} />
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="text-2xl font-semibold text-slate-900">{value}</div>
      <div className="text-xs text-slate-500 mt-1">{label}</div>
    </div>
  );
}
