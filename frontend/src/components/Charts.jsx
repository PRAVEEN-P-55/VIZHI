import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CHART_PALETTE } from "../theme/tokens";

const axis = { stroke: "#62645D", fontSize: 11 };
const tooltipStyle = {
  contentStyle: {
    background: "#111210",
    border: "1px solid rgba(255,255,255,0.14)",
    borderRadius: 2,
    color: "#F4F4F0",
  },
};

export function TrendChart({ data }) {
  // data: [{date, count, predicted?, spike?}]
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#84E600" stopOpacity={0.24} />
            <stop offset="100%" stopColor="#84E600" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="date" {...axis} tick={{ fill: "#A3A39D" }} minTickGap={40} />
        <YAxis {...axis} tick={{ fill: "#A3A39D" }} width={30} />
        <Tooltip {...tooltipStyle} />
        <Area
          type="monotone"
          dataKey="count"
          stroke="#84E600"
          fill="url(#g1)"
          strokeWidth={2}
        />
        <Area
          type="monotone"
          dataKey="predicted"
          stroke="#5DD6C0"
          strokeDasharray="4 3"
          fill="none"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function TypeDonut({ data }) {
  // data: [{name, value}]
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius={55}
          outerRadius={85}
          paddingAngle={2}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={CHART_PALETTE[i % CHART_PALETTE.length]} />
          ))}
        </Pie>
        <Tooltip {...tooltipStyle} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function DistrictBar({ data }) {
  // data: [{name, value}]
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} layout="vertical" margin={{ left: 20 }}>
        <XAxis type="number" {...axis} tick={{ fill: "#A3A39D" }} />
        <YAxis
          type="category"
          dataKey="name"
          {...axis}
          tick={{ fill: "#A3A39D" }}
          width={90}
        />
        <Tooltip {...tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={CHART_PALETTE[i % CHART_PALETTE.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function Legend({ items }) {
  return (
    <div className="flex flex-wrap gap-3 mt-2">
      {items.map((it, i) => (
        <div key={it} className="flex items-center gap-1.5 text-xs text-muted">
          <span
            className="w-2.5 h-2.5 rounded-full"
            style={{ background: CHART_PALETTE[i % CHART_PALETTE.length] }}
          />
          {it}
        </div>
      ))}
    </div>
  );
}
