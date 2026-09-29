import { useEffect, useState } from "react";
import client from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Card, Skeleton, SeverityBadge } from "../components/ui";

const SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
const CHANNELS = ["in_app", "sms", "email", "api"];

export default function Alerts() {
  const { user } = useAuth();
  const [alerts, setAlerts] = useState(null);
  const [capabilities, setCapabilities] = useState({ in_app: true });
  const [form, setForm] = useState({ severity: "HIGH", district: "", message: "", channels: ["in_app"] });
  const [sending, setSending] = useState(false);
  const [flash, setFlash] = useState(null);
  const canDispatch = user?.role === "i4c_admin" || user?.role === "state_lea";

  const load = () => client.get("/alerts?limit=100").then(({ data }) => setAlerts(data.items));
  useEffect(() => {
    load();
    client.get("/alerts/capabilities").then(({ data }) => setCapabilities(data));
  }, []);

  const toggleChannel = (channel) => setForm((current) => ({
    ...current,
    channels: current.channels.includes(channel) ? current.channels.filter((item) => item !== channel) : [...current.channels, channel],
  }));

  const dispatch = async () => {
    setSending(true);
    setFlash(null);
    try {
      const { data } = await client.post("/alerts/dispatch", { ...form, district: form.district || null, message: form.message || null });
      setFlash(data.deduped ? "Duplicate suppressed within the configured window." : "Action dispatched and configured channels notified.");
      await load();
    } catch (error) {
      setFlash(error.response?.data?.detail || "Unable to dispatch action.");
    } finally {
      setSending(false);
      window.setTimeout(() => setFlash(null), 6000);
    }
  };

  return (
    <div className="space-y-5">
      <div><h1 className="text-2xl font-bold tracking-tight">Alerts and response</h1><p className="text-sm text-muted">Review operational alerts and coordinate jurisdiction-aware intervention.</p></div>
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className={canDispatch ? "lg:col-span-2" : "lg:col-span-3"}>
          <Card title="Alert timeline">
            {!alerts ? <div className="space-y-2">{[...Array(6)].map((_, index) => <Skeleton key={index} className="h-16" />)}</div> : alerts.length === 0 ? <div className="text-sm text-muted">No alerts in your scope.</div> : (
              <div className="space-y-2">{alerts.map((alert) => <article key={alert.id} className="flex items-start justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><SeverityBadge level={alert.severity} /><span className="text-sm font-semibold">{alert.title}</span></div><p className="mt-1 text-sm text-muted">{alert.message}</p><div className="mt-1 text-xs text-muted">{alert.created_at}{alert.district && ` · ${alert.district}`}{alert.complaint_id && ` · ${alert.complaint_id}`}{alert.channels?.length > 0 && ` · delivered via ${alert.channels.join(", ")}`}</div></div><span className="ml-2 shrink-0 text-xs font-semibold uppercase text-muted">{alert.status}</span></article>)}</div>
            )}
          </Card>
        </div>

        {canDispatch && <Card title="Dispatch action">
          <div className="space-y-4">
            <div><div className="text-sm font-semibold">Severity</div><div className="mt-1.5 grid grid-cols-2 gap-2">{SEVERITIES.map((severity) => <button key={severity} aria-pressed={form.severity === severity} onClick={() => setForm({ ...form, severity })} className={`min-h-11 rounded-lg border text-xs font-semibold ${form.severity === severity ? "border-blue-300 bg-blue-50 text-accent" : "border-slate-200 bg-white text-muted"}`}>{severity}</button>)}</div></div>
            <label className="block text-sm font-semibold"><span className="mb-1.5 block">District</span><input value={form.district} onChange={(event) => setForm({ ...form, district: event.target.value })} placeholder="e.g. Coimbatore" className="min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 font-normal focus:border-accent" /></label>
            <label className="block text-sm font-semibold"><span className="mb-1.5 block">Action details</span><textarea value={form.message} onChange={(event) => setForm({ ...form, message: event.target.value })} rows={3} placeholder="Field action details…" className="w-full resize-none rounded-xl border border-slate-300 bg-white px-3 py-2 font-normal focus:border-accent" /></label>
            <div><div className="text-sm font-semibold">Delivery channels</div><div className="mt-1.5 grid grid-cols-2 gap-2">{CHANNELS.map((channel) => { const available = capabilities[channel]; return <button key={channel} aria-pressed={form.channels.includes(channel)} disabled={!available} onClick={() => toggleChannel(channel)} className={`min-h-11 rounded-lg border text-xs font-semibold ${form.channels.includes(channel) ? "border-blue-300 bg-blue-50 text-accent" : "border-slate-200 bg-white text-muted"} disabled:cursor-not-allowed disabled:opacity-45`}>{channel.replace("in_app", "in-app")}{!available && " · not configured"}</button>; })}</div></div>
            <button onClick={dispatch} disabled={sending || form.channels.length === 0} className="min-h-11 w-full rounded-xl bg-accent font-semibold text-white disabled:opacity-50">{sending ? "Dispatching…" : "Dispatch team"}</button>
            {flash && <div className="rounded-lg bg-blue-50 p-3 text-sm text-accent" role="status">{flash}</div>}
            <p className="text-xs text-muted">De-duplication is persisted in the database. Email, SMS, and API delivery activate only when their providers are configured.</p>
          </div>
        </Card>}
      </div>
    </div>
  );
}
