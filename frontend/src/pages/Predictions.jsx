import { useEffect, useState } from "react";
import client from "../api/client";
import { Card, Skeleton, RiskBadge } from "../components/ui";

export default function Predictions() {
  const [preds, setPreds] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [scope, setScope] = useState("");
  const [windowHrs, setWindowHrs] = useState(48);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError("");
    setSelected(null);
    client.post("/predict", { window_hrs: windowHrs })
      .then(({ data }) => {
        if (!alive) return;
        setPreds(data.predictions);
        setMetrics(data.metrics);
        setScope(data.scope);
      })
      .catch((requestError) => alive && setError(requestError.response?.data?.detail || "Unable to load predictions."))
      .finally(() => alive && setLoading(false));
    return () => (alive = false);
  }, [windowHrs]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Predictive intelligence</h1>
        <p className="text-sm text-muted">Ranked district risk and likely cash-out destinations for the selected operational horizon.</p>
      </div>
      {error && <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-danger" role="alert">{error}</div>}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-muted">
          <span>Prediction window:</span>
          {[24, 48, 72].map((h) => (
            <button
              key={h}
              onClick={() => setWindowHrs(h)}
              aria-pressed={windowHrs === h}
              className={`min-h-11 px-3 py-1.5 rounded-lg border text-sm ${
                windowHrs === h
                  ? "border-accent/40 text-accent bg-accent/10"
                  : "border-slate-300 bg-white text-muted"
              }`}
            >
              {h}h
            </button>
          ))}
          <span className="ml-2 text-xs">scope: {scope}</span>
        </div>
        {metrics && (
          <div className="flex gap-4 text-xs text-muted">
            <span>
              backend: <span className="text-text">{metrics.backend}</span>
            </span>
            <span>
              macro-F1: <span className="text-accent">{metrics.macro_f1}</span>
            </span>
            <span>
              P@5: <span className="text-accent">{metrics.precision_at_5}</span>
            </span>
            {metrics.cashout_top_3_accuracy != null && (
              <span>
                cash-out Top-3: <span className="text-accent">{Math.round(metrics.cashout_top_3_accuracy * 100)}%</span>
              </span>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <Card title="Ranked District Risk (next window)">
            {loading ? (
              <div className="space-y-2">
                {[...Array(8)].map((_, i) => (
                  <Skeleton key={i} className="h-10" />
                ))}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-muted text-xs uppercase tracking-wider border-b border-slate-200">
                      <th className="py-2 pr-3">#</th>
                      <th className="py-2 pr-3">District</th>
                      <th className="py-2 pr-3">Risk</th>
                      <th className="py-2 pr-3">P(HIGH)</th>
                      <th className="py-2 pr-3">Likely cash-out →</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(preds || []).map((p, i) => (
                      <tr
                        key={p.district}
                        onClick={() => setSelected(p)}
                        className={`border-b border-slate-100 cursor-pointer hover:bg-slate-50 ${
                          selected?.district === p.district ? "bg-accent/10" : ""
                        }`}
                      >
                        <td className="py-2 pr-3 text-muted">{i + 1}</td>
                        <td className="py-2 pr-3 font-medium">{p.district}</td>
                        <td className="py-2 pr-3">
                          <RiskBadge level={p.risk_level} />
                        </td>
                        <td className="py-2 pr-3 text-accent">
                          {(p.p_high * 100).toFixed(0)}%
                        </td>
                        <td className="py-2 pr-3 text-muted text-xs">
                          {p.likely_cashout_districts
                            .map((c) => c.withdrawal_district)
                            .join(", ") || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>

        <Card title="Explainability">
          {!selected ? (
            <div className="text-sm text-muted">
              Select a district to view its SHAP-based key indicators and predicted
              cash-out flow.
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <div className="text-lg font-semibold">{selected.district}</div>
                <div className="text-xs text-muted">
                  {selected.state} · confidence {(selected.confidence * 100).toFixed(0)}%
                </div>
              </div>

              <div>
                <div className="text-xs uppercase tracking-wider text-muted mb-1">
                  Key Indicators
                </div>
                <div className="space-y-1">
                  {selected.key_indicators.map((k, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between text-sm bg-bg rounded px-2 py-1.5"
                    >
                      <span>{k.label}</span>
                      <span
                        className={k.direction === "raises" ? "text-danger" : "text-safe"}
                      >
                        {k.impact > 0 ? "+" : ""}
                        {k.impact.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="text-xs uppercase tracking-wider text-muted mb-1">
                  Likely Cash-out Districts
                </div>
                <div className="space-y-1">
                  {selected.likely_cashout_districts.map((c, i) => (
                    <div key={i} className="text-sm bg-bg rounded px-2 py-1.5">
                      <span className="font-medium">{c.withdrawal_district}</span>
                      <span className="text-muted text-xs">
                        {" "}
                        · p={c.probability} · ~{c.median_lag_hrs}h lag · {c.count} historical
                      </span>
                    </div>
                  ))}
                  {!selected.likely_cashout_districts.length && (
                    <div className="text-sm text-muted">No historical pattern.</div>
                  )}
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
