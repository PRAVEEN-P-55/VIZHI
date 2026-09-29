import { SEVERITY_COLORS, RISK_COLORS } from "../theme/tokens";

export function Card({ title, children, className = "", action }) {
  return (
    <div
      className={`bg-surface/95 rounded-2xl border border-white/10 shadow-glow ${className}`}
    >
      {title && (
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
          <h3 className="font-mono text-xs font-semibold uppercase tracking-[0.12em] text-text">
            {title}
          </h3>
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

export function StatCard({ label, value, sub, tone = "accent" }) {
  const toneMap = {
    accent: "text-accent",
    danger: "text-danger",
    safe: "text-safe",
    text: "text-text",
  };
  return (
    <div className="bg-surface/95 rounded-2xl border border-white/10 p-5 shadow-glow">
      <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted">// {label}</div>
      <div className={`text-3xl font-bold mt-1 ${toneMap[tone]}`}>{value}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  );
}

export function Skeleton({ className = "h-4 w-full" }) {
  return <div className={`skeleton ${className}`} />;
}

export function SeverityBadge({ level }) {
  const c = SEVERITY_COLORS[level] || SEVERITY_COLORS.UNKNOWN;
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap"
      style={{ background: `${c}22`, color: c, border: `1px solid ${c}55` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: c }} aria-hidden="true" />
      {level}
    </span>
  );
}

export function RiskBadge({ level }) {
  const c = RISK_COLORS[level] || RISK_COLORS.UNKNOWN;
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap"
      style={{ background: `${c}22`, color: c, border: `1px solid ${c}55` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: c }} aria-hidden="true" />
      {level}
    </span>
  );
}
