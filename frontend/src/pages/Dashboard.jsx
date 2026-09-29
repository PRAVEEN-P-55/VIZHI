import { useEffect, useState } from "react";
import client from "../api/client";
import { Card, StatCard, Skeleton, RiskBadge, SeverityBadge } from "../components/ui";
import RiskMap from "../components/RiskMap";
import { TrendChart, TypeDonut, DistrictBar, Legend } from "../components/Charts";
import { inr } from "../theme/tokens";

export default function Dashboard() {
  const [d, setD] = useState({});
  const [loading, setLoading] = useState(true);
  const [drill, setDrill] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [pred, heat, layers, stats, forecast, golden, alerts] = await Promise.all([
          client.post("/predict", { top_k: 5 }),
          client.get("/heatmap"),
          client.get("/map/layers"),
          client.get("/complaints/stats"),
          client.get("/forecast"),
          client.get("/golden-hour"),
          client.get("/alerts?limit=8"),
        ]);
        if (!alive) return;
        setD({
          pred: pred.data,
          zones: heat.data.zones,
          layers: layers.data,
          stats: stats.data,
          forecast: forecast.data,
          golden: golden.data,
          alerts: alerts.data.items,
        });
      } catch (requestError) {
        if (alive) setError(requestError.response?.data?.detail || "Unable to load the command dashboard.");
      } finally {
        alive && setLoading(false);
      }
    })();
    return () => (alive = false);
  }, []);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (error || !d.stats) {
    return <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-danger" role="alert">{error || "Dashboard data is unavailable."}</div>;
  }

  const trend = mergeForecast(d.forecast);
  const typeData = Object.entries(d.stats.by_type).map(([name, value]) => ({ name, value }));
  const districtData = Object.entries(d.stats.by_district).map(([name, value]) => ({
    name,
    value,
  }));
  const critical = d.golden.counts?.critical || 0;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Command overview</h1>
        <p className="text-sm text-muted">Live operational picture for the Tamil Nadu pilot.</p>
      </div>
      {/* live stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Complaints (total)"
          value={d.stats.total_complaints.toLocaleString("en-IN")}
          sub={inr(d.stats.total_fraud_amount) + " fraud reported"}
        />
        <StatCard
          label="High-risk zones"
          value={d.pred.predictions.filter((p) => p.risk_level === "HIGH").length}
          sub={`scope: ${d.pred.scope}`}
          tone="danger"
        />
        <StatCard
          label="Golden-hour critical"
          value={critical}
          sub="complaints in 6–18h window"
          tone="accent"
        />
        <StatCard
          label="Active alerts"
          value={d.alerts.length}
          sub="last raised events"
          tone="danger"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* map */}
        <div className="lg:col-span-2">
          <Card title="Tamil Nadu risk map">
            <RiskMap zones={d.zones} layers={d.layers} onDrill={setDrill} />
            {drill && (
              <div className="mt-3 text-sm bg-blue-50 rounded-xl p-3 border border-blue-200">
                <b className="text-accent">{drill.dominant_district}</b> — predicted{" "}
                <RiskBadge level={drill.predicted_risk} /> · {drill.withdrawal_count}{" "}
                withdrawals · {inr(drill.total_amount)} · near{" "}
                {drill.near_landmark || "—"}
              </div>
            )}
          </Card>
        </div>

        {/* top-5 hotspots + golden hour */}
        <div className="space-y-5">
          <Card title="Top-5 Predicted Hotspots">
            <div className="space-y-2">
              {d.pred.predictions.map((p, i) => (
                <div
                  key={p.district}
                  className="flex items-center justify-between bg-slate-50 rounded-xl px-3 py-2 border border-slate-200"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-muted text-sm w-4">{i + 1}</span>
                    <div>
                      <div className="text-sm font-medium">{p.district}</div>
                      <div className="text-[11px] text-muted">
                        → {p.likely_cashout_districts[0]?.withdrawal_district || "—"}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <RiskBadge level={p.risk_level} />
                    <div className="text-[11px] text-muted mt-0.5">
                      {(p.p_high * 100).toFixed(0)}% P(HIGH)
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Golden Hour tracker">
            <GoldenHour items={d.golden.items} />
          </Card>
        </div>
      </div>

      {/* charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <Card title="Complaint Trend + Forecast" className="lg:col-span-2">
          <TrendChart data={trend} />
          <div className="text-xs text-muted mt-1">
            Solid = actual · dashed = {d.forecast.backend} forecast (baseline{" "}
            {d.forecast.baseline}/day)
          </div>
        </Card>
        <Card title="Fraud Type Mix">
          <TypeDonut data={typeData} />
          <Legend items={typeData.map((t) => t.name)} />
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card title="Complaints by District (top 10)">
          <DistrictBar data={districtData} />
        </Card>
        <Card title="Recent Alerts">
          <div className="space-y-2">
            {d.alerts.map((a) => (
              <div
                key={a.id}
                className="flex items-center justify-between bg-slate-50 rounded-xl px-3 py-2 border border-slate-200"
              >
                <div>
                  <div className="text-sm">{a.title}</div>
                  <div className="text-[11px] text-muted">{a.created_at}</div>
                </div>
                <SeverityBadge level={a.severity} />
              </div>
            ))}
            {d.alerts.length === 0 && (
              <div className="text-sm text-muted">No alerts in scope.</div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

function GoldenHour({ items }) {
  const critical = items.filter((i) => i.phase === "critical").slice(0, 5);
  if (!critical.length)
    return <div className="text-sm text-muted">No complaints in critical window.</div>;
  return (
    <div className="space-y-2">
      {critical.map((c) => (
        <div key={c.complaint_id} className="bg-bg rounded-lg px-3 py-2 border border-accent/20">
          <div className="flex justify-between">
            <span className="text-sm font-medium">{c.district}</span>
            <span className="text-accent text-sm font-bold">
              {c.hrs_left_in_window}h left
            </span>
          </div>
          <div className="text-[11px] text-muted">
            {c.complaint_type} · {inr(c.fraud_amount)} · {c.complaint_id}
          </div>
        </div>
      ))}
    </div>
  );
}

function mergeForecast(f) {
  const hist = (f.history || []).map((h) => ({ date: h.date, count: h.count }));
  const fc = (f.forecast || []).map((h) => ({ date: h.date, predicted: h.predicted }));
  return [...hist, ...fc];
}
