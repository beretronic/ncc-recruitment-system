import { useState } from "react";
import { Link } from "react-router-dom";
import { applicantRegister } from "../api/auth";

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

const inputClass =
  "w-full rounded-[11px] border border-white/90 px-3.5 py-3 text-sm outline-none focus:ring-2 transition";
const inputStyle = { background: "rgba(255,255,255,0.7)", color: "#16341f" };

export default function Register() {
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    phone: "",
    address: "",
    date_of_birth: "",
    gender: "",
    education_level: "",
    years_of_experience: "",
    national_id_number: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  function update(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await applicantRegister({
        ...form,
        years_of_experience: form.years_of_experience
          ? Number(form.years_of_experience)
          : 0,
      });
      setSuccess(true);
    } catch (err: any) {
      const data = err?.response?.data;
      const firstError =
        data && typeof data === "object"
          ? (Object.values(data)[0] as string[])?.[0]
          : null;
      setError(firstError || "Registration failed. Please check your details.");
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden" style={glassBg}>
        <Blobs />
        <div
          className="relative w-full max-w-sm rounded-[22px] border border-white/80 backdrop-blur-2xl px-10 py-11 text-center"
          style={{ background: "rgba(255,255,255,0.55)", boxShadow: "0 30px 70px rgba(30,90,50,0.18)" }}
        >
          <h1 className="text-xl font-bold mb-2" style={{ color: "#123321" }}>
            Almost there
          </h1>
          <p className="text-sm mb-7" style={{ color: "#4a6b56" }}>
            We've sent a verification code to your email. Enter it on the
            verify page to activate your account.
          </p>
          <Link
            to="/verify"
            className="inline-block w-full rounded-[11px] py-3.5 text-sm font-bold text-white transition"
            style={{ background: "#4EA72E", boxShadow: "0 14px 28px rgba(78,167,46,0.35)" }}
          >
            Go to verification
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10 relative overflow-hidden" style={glassBg}>
      <Blobs />
      <div
        className="relative w-full max-w-lg rounded-[22px] border border-white/80 backdrop-blur-2xl px-10 py-11"
        style={{ background: "rgba(255,255,255,0.55)", boxShadow: "0 30px 70px rgba(30,90,50,0.18)" }}
      >
        <h1 className="text-xl font-bold" style={{ color: "#123321" }}>
          Create your applicant account
        </h1>
        <p className="text-sm mt-1 mb-7" style={{ color: "#4a6b56" }}>
          This profile will be reused every time you apply for a vacancy.
        </p>

        <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Full name" required span2>
            <input required value={form.full_name} onChange={(e) => update("full_name", e.target.value)} className={inputClass} style={inputStyle} />
          </Field>

          <Field label="Email" required span2>
            <input type="email" required value={form.email} onChange={(e) => update("email", e.target.value)} className={inputClass} style={inputStyle} />
          </Field>

          <Field label="Password" required span2>
            <input type="password" required minLength={8} value={form.password} onChange={(e) => update("password", e.target.value)} className={inputClass} style={inputStyle} />
          </Field>

          <Field label="Phone">
            <input value={form.phone} onChange={(e) => update("phone", e.target.value)} className={inputClass} style={inputStyle} />
          </Field>

          <Field label="National ID number">
            <input value={form.national_id_number} onChange={(e) => update("national_id_number", e.target.value)} className={inputClass} style={inputStyle} />
          </Field>

          <Field label="Address" span2>
            <input value={form.address} onChange={(e) => update("address", e.target.value)} className={inputClass} style={inputStyle} />
          </Field>

          <Field label="Date of birth">
            <input type="date" value={form.date_of_birth} onChange={(e) => update("date_of_birth", e.target.value)} className={inputClass} style={inputStyle} />
          </Field>

          <Field label="Gender">
            <select value={form.gender} onChange={(e) => update("gender", e.target.value)} className={inputClass} style={inputStyle}>
              <option value="">Select...</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </Field>

          <Field label="Education level">
            <input value={form.education_level} onChange={(e) => update("education_level", e.target.value)} className={inputClass} style={inputStyle} placeholder="e.g. Bachelor's Degree" />
          </Field>

          <Field label="Years of experience">
            <input type="number" min={0} value={form.years_of_experience} onChange={(e) => update("years_of_experience", e.target.value)} className={inputClass} style={inputStyle} />
          </Field>

          {error && (
            <p className="sm:col-span-2 text-sm text-red-700 bg-red-50/80 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="sm:col-span-2 rounded-[11px] py-3.5 text-sm font-bold text-white disabled:opacity-60 transition"
            style={{ background: "#4EA72E", boxShadow: "0 14px 28px rgba(78,167,46,0.35)" }}
          >
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="text-sm mt-5 text-center" style={{ color: "#4a6b56" }}>
          Already have an account?{" "}
          <Link to="/login" className="font-bold" style={{ color: "#2e7d32" }}>
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

function Field({
  label,
  required,
  span2,
  children,
}: {
  label: string;
  required?: boolean;
  span2?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={span2 ? "sm:col-span-2" : ""}>
      <label className="block text-xs font-bold mb-1.5" style={{ color: "#33553f" }}>
        {label} {required && <span style={{ color: "#c0392b" }}>*</span>}
      </label>
      {children}
    </div>
  );
}
