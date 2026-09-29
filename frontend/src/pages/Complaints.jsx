import { useEffect, useState } from "react";
import client from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Card, Skeleton } from "../components/ui";
import { inr } from "../theme/tokens";

const TYPES = ["UPI Fraud", "OTP Scam", "KYC Fraud", "Job Fraud", "Loan App Fraud"];
const STATUSES = ["open", "under_investigation", "resolved", "closed"];
const BANKS = ["SBI", "HDFC", "ICICI", "Axis Bank", "Canara Bank", "Paytm"];

const initialForm = {
  state: "Tamil Nadu",
  district: "Coimbatore",
  pin_code: "641001",
  lat: "11.0168",
  lon: "76.9558",
  complaint_type: "UPI Fraud",
  fraud_amount: "45000",
  reported_bank: "SBI",
  victim_account_type: "savings",
};

export default function Complaints() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ complaint_type: "", status: "", search: "" });
  const [showIntake, setShowIntake] = useState(false);
  const [form, setForm] = useState(() => ({
    ...initialForm,
    state: user?.role === "state_lea" ? user.scope_value : initialForm.state,
    reported_bank: user?.role === "bank_officer" ? user.scope_value : initialForm.reported_bank,
  }));
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [outcomeFor, setOutcomeFor] = useState(null);
  const [outcome, setOutcome] = useState({ action: "Bank freeze request", outcome: "pending", amount_blocked: "0", amount_recovered: "0", notes: "" });
  const [outcomeFlash, setOutcomeFlash] = useState("");

  const load = () => {
    setLoading(true);
    const params = new URLSearchParams({ page, page_size: 25 });
    if (filters.complaint_type) params.set("complaint_type", filters.complaint_type);
    if (filters.status) params.set("status", filters.status);
    if (filters.search) params.set("search", filters.search);
    return client.get(`/complaints?${params}`).then(({ data: response }) => setData(response)).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [page, filters]);

  const setFilter = (key, value) => {
    setPage(1);
    setFilters((current) => ({ ...current, [key]: value }));
  };

  const submitComplaint = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const payload = { ...form, lat: Number(form.lat), lon: Number(form.lon), fraud_amount: Number(form.fraud_amount) };
      const { data: response } = await client.post("/complaints", payload);
      setResult(response);
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to register complaint.");
    } finally {
      setSubmitting(false);
    }
  };

  const exportCSV = () => {
    if (!data?.items?.length) return;
    const columns = Object.keys(data.items[0]);
    const rows = [columns.join(",")].concat(
      data.items.map((row) => columns.map((column) => `"${String(row[column] ?? "").replace(/"/g, '""')}"`).join(","))
    );
    const url = URL.createObjectURL(new Blob([rows.join("\n")], { type: "text/csv" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `vizhi_complaints_page_${page}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const recordOutcome = async (event) => {
    event.preventDefault();
    try {
      await client.post(`/complaints/${encodeURIComponent(outcomeFor)}/outcomes`, {
        ...outcome,
        amount_blocked: Number(outcome.amount_blocked),
        amount_recovered: Number(outcome.amount_recovered),
      });
      setOutcomeFlash("Outcome recorded in the audit trail and feedback dataset.");
      window.setTimeout(() => { setOutcomeFlash(""); setOutcomeFor(null); }, 2500);
    } catch (requestError) {
      setOutcomeFlash(requestError.response?.data?.detail || "Unable to record outcome.");
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Complaint operations</h1>
          <p className="text-sm text-muted">Register a case and receive an immediate 48-hour cash-out forecast.</p>
        </div>
        <button onClick={() => setShowIntake((open) => !open)} className="min-h-11 rounded-xl bg-accent px-4 text-sm font-semibold text-white hover:bg-blue-700">
          {showIntake ? "Close intake" : "Register complaint"}
        </button>
      </div>

      {showIntake && (
        <Card title="New live complaint">
          <form onSubmit={submitComplaint} className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Field label="State"><input required value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} /></Field>
            <Field label="District"><input required value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} /></Field>
            <Field label="PIN code"><input required pattern="[0-9]{6}" value={form.pin_code} onChange={(e) => setForm({ ...form, pin_code: e.target.value })} /></Field>
            <Field label="Fraud amount (₹)"><input required type="number" min="1" value={form.fraud_amount} onChange={(e) => setForm({ ...form, fraud_amount: e.target.value })} /></Field>
            <Field label="Fraud type"><select value={form.complaint_type} onChange={(e) => setForm({ ...form, complaint_type: e.target.value })}>{TYPES.map((type) => <option key={type}>{type}</option>)}</select></Field>
            <Field label="Reported bank"><select value={form.reported_bank} disabled={user?.role === "bank_officer"} onChange={(e) => setForm({ ...form, reported_bank: e.target.value })}>{BANKS.map((bank) => <option key={bank}>{bank}</option>)}</select></Field>
            <Field label="Latitude"><input required type="number" step="any" value={form.lat} onChange={(e) => setForm({ ...form, lat: e.target.value })} /></Field>
            <Field label="Longitude"><input required type="number" step="any" value={form.lon} onChange={(e) => setForm({ ...form, lon: e.target.value })} /></Field>
            <div className="md:col-span-2 lg:col-span-4 flex items-center gap-3">
              <button disabled={submitting} className="min-h-11 rounded-xl bg-accent px-5 text-sm font-semibold text-white disabled:opacity-50">{submitting ? "Analyzing…" : "Register and predict"}</button>
              {error && <span className="text-sm text-danger" role="alert">{error}</span>}
            </div>
          </form>
          {result && <PredictionResult result={result} />}
        </Card>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <input aria-label="Search complaint ID" placeholder="Search complaint ID…" value={filters.search} onChange={(e) => setFilter("search", e.target.value)} className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm focus:border-accent" />
        <select aria-label="Filter by complaint type" value={filters.complaint_type} onChange={(e) => setFilter("complaint_type", e.target.value)} className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm"><option value="">All types</option>{TYPES.map((type) => <option key={type}>{type}</option>)}</select>
        <select aria-label="Filter by status" value={filters.status} onChange={(e) => setFilter("status", e.target.value)} className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm"><option value="">All statuses</option>{STATUSES.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select>
        <div className="flex-1" />
        <button onClick={exportCSV} className="min-h-11 rounded-xl border border-blue-200 bg-blue-50 px-4 text-sm font-semibold text-accent">Export CSV</button>
      </div>

      <Card title={`Complaints ${data ? `(${data.total.toLocaleString("en-IN")})` : ""}`}>
        {loading ? <div className="space-y-2">{[...Array(8)].map((_, index) => <Skeleton key={index} className="h-10" />)}</div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-slate-200 text-left text-xs font-semibold uppercase tracking-wider text-muted"><th className="py-3 pr-3">ID</th><th className="py-3 pr-3">Filed</th><th className="py-3 pr-3">District</th><th className="py-3 pr-3">Type</th><th className="py-3 pr-3">Amount</th><th className="py-3 pr-3">Bank</th><th className="py-3 pr-3">Status</th><th className="py-3">Action</th></tr></thead>
              <tbody>{data?.items.map((complaint) => <tr key={complaint.complaint_id} className="border-b border-slate-100 hover:bg-slate-50"><td className="py-3 pr-3 font-mono text-xs font-semibold text-accent">{complaint.complaint_id}</td><td className="py-3 pr-3 text-muted">{complaint.timestamp}</td><td className="py-3 pr-3">{complaint.district}</td><td className="py-3 pr-3">{complaint.complaint_type}</td><td className="py-3 pr-3">{inr(complaint.fraud_amount)}</td><td className="py-3 pr-3 text-muted">{complaint.reported_bank}</td><td className="py-3 pr-3 capitalize text-muted">{complaint.complaint_status?.replaceAll("_", " ")}</td><td className="py-3"><button onClick={() => setOutcomeFor(complaint.complaint_id)} className="min-h-11 whitespace-nowrap rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-accent">Record outcome</button></td></tr>)}</tbody>
            </table>
          </div>
        )}
      </Card>

      {outcomeFor && <Card title={`Intervention outcome · ${outcomeFor}`}><form onSubmit={recordOutcome} className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4"><Field label="Action"><input required value={outcome.action} onChange={(event) => setOutcome({ ...outcome, action: event.target.value })} /></Field><Field label="Outcome"><select value={outcome.outcome} onChange={(event) => setOutcome({ ...outcome, outcome: event.target.value })}><option value="pending">Pending</option><option value="blocked">Blocked</option><option value="recovered">Recovered</option><option value="withdrawn">Withdrawn</option><option value="false_positive">False positive</option></select></Field><Field label="Amount blocked (₹)"><input type="number" min="0" value={outcome.amount_blocked} onChange={(event) => setOutcome({ ...outcome, amount_blocked: event.target.value })} /></Field><Field label="Amount recovered (₹)"><input type="number" min="0" value={outcome.amount_recovered} onChange={(event) => setOutcome({ ...outcome, amount_recovered: event.target.value })} /></Field><label className="md:col-span-2 lg:col-span-4 text-sm font-medium"><span className="mb-1.5 block">Notes</span><textarea rows="2" value={outcome.notes} onChange={(event) => setOutcome({ ...outcome, notes: event.target.value })} className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2" /></label><div className="flex items-center gap-3 md:col-span-2 lg:col-span-4"><button className="min-h-11 rounded-xl bg-accent px-5 text-sm font-semibold text-white">Save outcome</button><button type="button" onClick={() => setOutcomeFor(null)} className="min-h-11 rounded-xl border border-slate-300 bg-white px-5 text-sm font-semibold">Cancel</button>{outcomeFlash && <span className="text-sm text-accent" role="status">{outcomeFlash}</span>}</div></form></Card>}

      {data && <div className="flex items-center justify-between text-sm text-muted"><span>Page {data.page} of {data.pages}</span><div className="flex gap-2"><button disabled={page <= 1} onClick={() => setPage((value) => value - 1)} className="min-h-11 rounded-xl border border-slate-300 bg-white px-4 disabled:opacity-40">Previous</button><button disabled={page >= data.pages} onClick={() => setPage((value) => value + 1)} className="min-h-11 rounded-xl border border-slate-300 bg-white px-4 disabled:opacity-40">Next</button></div></div>}
    </div>
  );
}

function Field({ label, children }) {
  return <label className="text-sm font-medium text-text"><span className="mb-1.5 block">{label}</span><span className="[&>input]:min-h-11 [&>input]:w-full [&>input]:rounded-xl [&>input]:border [&>input]:border-slate-300 [&>input]:bg-white [&>input]:px-3 [&>select]:min-h-11 [&>select]:w-full [&>select]:rounded-xl [&>select]:border [&>select]:border-slate-300 [&>select]:bg-white [&>select]:px-3">{children}</span></label>;
}

function PredictionResult({ result }) {
  return <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 p-4"><div className="font-semibold text-text">Complaint {result.complaint.complaint_id} registered</div><p className="mt-1 text-sm text-muted">Top predicted cash-out zones for the next 48 hours:</p><div className="mt-3 grid gap-3 md:grid-cols-3">{result.prediction.destinations.map((destination) => <div key={destination.withdrawal_district} className="rounded-xl border border-blue-100 bg-white p-3"><div className="flex items-center justify-between"><span className="font-semibold">#{destination.rank} {destination.withdrawal_district}</span><span className="text-sm font-bold text-accent">{Math.round(destination.probability * 100)}%</span></div><div className="mt-1 text-xs text-muted">{destination.time_bucket} · {inr(destination.expected_amount)} expected</div></div>)}</div></div>;
}
