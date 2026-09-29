import { useEffect, useState } from "react";
import client from "../api/client";
import { Card, Skeleton, RiskBadge } from "../components/ui";
import { inr } from "../theme/tokens";

export default function Intelligence() {
  const [district, setDistrict] = useState("Coimbatore");
  const [brief, setBrief] = useState(null);
  const [busy, setBusy] = useState(false);
  const [dna, setDna] = useState(null);
  const [revic, setRevic] = useState(null);

  useEffect(() => {
    client.get("/dna").then(({ data }) => setDna(data));
    client.get("/revictimization").then(({ data }) => setRevic(data));
    genBrief("Coimbatore");
  }, []);

  const genBrief = async (dist) => {
    setBusy(true);
    try {
      const { data } = await client.get(`/agent/brief/${encodeURIComponent(dist)}`);
      setBrief(data);
    } finally {
      setBusy(false);
    }
  };

  const exportPDF = async () => {
    if (!brief?.brief_text) return;
    const { jsPDF } = await import("jspdf");
    const doc = new jsPDF();
    doc.setFontSize(16);
    doc.text("VIZHI Intelligence Brief", 14, 18);
    doc.setFontSize(10);
    doc.text(`I4C / CIS Division — generated ${new Date().toLocaleString()}`, 14, 25);
    doc.setDrawColor(245, 158, 11);
    doc.line(14, 28, 196, 28);
    let y = 38;
    doc.setFontSize(11);
    brief.brief_text.split("\n").forEach((ln) => {
      doc.text(ln, 14, y);
      y += 7;
    });
    doc.save(`brief_${district}.pdf`);
  };

  return (
    <div className="space-y-5">
      <div><h1 className="text-2xl font-bold tracking-tight">Intelligence workspace</h1><p className="text-sm text-muted">Generate evidence-grounded briefs and inspect linked fraud patterns.</p></div>
      <Card title="AI intelligence brief generator">
        <div className="flex flex-wrap gap-2 mb-4">
          <input
            value={district}
            onChange={(e) => setDistrict(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && genBrief(district)}
            placeholder="District name…"
            className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm focus:border-accent"
          />
          <button
            onClick={() => genBrief(district)}
            disabled={busy}
            className="min-h-11 rounded-xl bg-accent px-4 text-sm font-semibold text-white disabled:opacity-50"
          >
            {busy ? "Generating…" : "Generate Brief"}
          </button>
          {brief?.brief_text && (
            <button
              onClick={exportPDF}
              className="px-4 py-2 rounded-lg bg-accent/15 text-accent border border-accent/20 text-sm"
            >
              ⬇ Export PDF
            </button>
          )}
        </div>

        {busy && <Skeleton className="h-48" />}
        {!busy && brief?.error && (
          <div className="text-sm text-danger">{brief.error}</div>
        )}
        {!busy && brief?.brief_text && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <pre className="whitespace-pre-wrap font-sans text-sm text-text/90">
                {brief.brief_text}
              </pre>
            </div>
            <div className="space-y-3">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs uppercase tracking-wider text-muted">Threat level</div>
                <div className="mt-1">
                  <RiskBadge level={brief.threat_level} />
                </div>
                <div className="text-xs text-muted mt-2">
                  Confidence {brief.confidence_score} · window {brief.time_window}
                </div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs uppercase tracking-wider text-muted mb-1">
                  Recommended action
                </div>
                <ul className="text-xs space-y-1 list-disc pl-4 text-text/80">
                  {brief.recommended_action?.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card
          title={`Complaint DNA rings ${
            dna ? `(${dna.organized_ring_count} organized)` : ""
          }`}
        >
          {!dna ? (
            <Skeleton className="h-40" />
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {dna.rings.map((r) => (
                <div
                  key={r.dna_id}
                  className={`bg-bg rounded-lg px-3 py-2 border ${
                    r.organized_ring ? "border-danger/30" : "border-slate-200"
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">
                      {r.dominant_type}
                      {r.organized_ring && (
                        <span className="ml-2 text-[10px] text-danger uppercase">
                          organized ring
                        </span>
                      )}
                    </span>
                    <span className="text-xs text-muted">{r.size} complaints</span>
                  </div>
                  <div className="text-[11px] text-muted mt-0.5">
                    {r.districts_spanned} districts · avg {inr(r.avg_fraud_amount)} · peak{" "}
                    {r.peak_hour}:00
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card
          title={`Re-victimization ${
            revic ? `(${revic.repeat_victim_count} repeat victims)` : ""
          }`}
        >
          {!revic ? (
            <Skeleton className="h-40" />
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {revic.items.map((v) => (
                <div
                  key={v.victim_key}
                  className="bg-bg rounded-lg px-3 py-2 border border-accent/20"
                >
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">{v.district}</span>
                    <span className="text-accent text-sm font-bold">
                      {v.complaint_count}× targeted
                    </span>
                  </div>
                  <div className="text-[11px] text-muted">
                    {inr(v.total_fraud_amount)} · {v.districts_targeted} districts · last{" "}
                    {v.last_complaint} · {v.risk_multiplier}
                  </div>
                </div>
              ))}
              {!revic.items.length && (
                <div className="text-sm text-muted">No repeat victims in scope.</div>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
