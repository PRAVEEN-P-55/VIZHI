// Shared severity / risk color tokens (mirrors tailwind.config.js + Section 7).
export const SEVERITY_COLORS = {
  LOW: "#9BEA63",
  MEDIUM: "#F5C451",
  HIGH: "#FF8A5B",
  CRITICAL: "#FF6B6B",
  UNKNOWN: "#A3A39D",
};

export const RISK_COLORS = {
  LOW: "#9BEA63",
  MEDIUM: "#F5C451",
  HIGH: "#FF6B6B",
  UNKNOWN: "#A3A39D",
};

// categorical palette for charts (accessible on the dark surface)
export const CHART_PALETTE = [
  "#84E600",
  "#5DD6C0",
  "#A78BFA",
  "#9BEA63",
  "#F5C451",
  "#FF7AB6",
];

export const inr = (n) =>
  n == null
    ? "—"
    : "₹" +
      Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });
