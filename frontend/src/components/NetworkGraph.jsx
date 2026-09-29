import { useEffect, useRef } from "react";
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide,
} from "d3-force";

const KIND_COLOR = {
  mule: "#FF6B6B",
  complaint: "#84E600",
  bank: "#5DD6C0",
};

// D3 force-directed fraud syndicate graph rendered into SVG via React refs.
export default function NetworkGraph({ nodes, edges, height = 520 }) {
  const svgRef = useRef(null);
  const wrapRef = useRef(null);

  useEffect(() => {
    if (!nodes?.length) return;
    const width = wrapRef.current?.clientWidth || 800;

    // clone so d3 can mutate x/y without touching props
    const N = nodes.map((n) => ({ ...n }));
    const L = edges.map((e) => ({ ...e }));
    const byId = new Map(N.map((n) => [n.id, n]));

    const sim = forceSimulation(N)
      .force(
        "link",
        forceLink(L)
          .id((d) => d.id)
          .distance((d) => (d.kind === "linked_complaint" ? 40 : 26))
          .strength(0.35)
      )
      .force("charge", forceManyBody().strength(-80))
      .force("center", forceCenter(width / 2, height / 2))
      .force("collide", forceCollide(8))
      .stop(); // run headless to avoid per-tick DOM thrash on large graphs

    const svg = svgRef.current;

    const render = () => {
      const lines = L.map((l) => {
        const s = byId.get(typeof l.source === "object" ? l.source.id : l.source);
        const t = byId.get(typeof l.target === "object" ? l.target.id : l.target);
        return `<line x1="${s.x}" y1="${s.y}" x2="${t.x}" y2="${t.y}" stroke="#3F413B" stroke-width="1"/>`;
      }).join("");
      const circles = N.map((n) => {
        const r = n.kind === "bank" ? 7 : n.kind === "mule" ? 5 : 3;
        const stroke = n.flagged ? "#FF6B6B" : "none";
        return `<circle cx="${n.x}" cy="${n.y}" r="${r}" fill="${
          KIND_COLOR[n.kind] || "#A3A39D"
        }" stroke="${stroke}" stroke-width="1.5"><title>${n.label} (${n.kind}${
          n.district ? " · " + n.district : ""
        })</title></circle>`;
      }).join("");
      svg.innerHTML = lines + circles;
    };

    // Compute a settled layout in one pass, then paint once.
    const ticks = Math.min(300, 60 + N.length);
    for (let i = 0; i < ticks; i++) sim.tick();
    render();

    return () => sim.stop();
  }, [nodes, edges, height]);

  return (
    <div ref={wrapRef} className="w-full">
      <svg
        ref={svgRef}
        width="100%"
        height={height}
        style={{ background: "#111210", borderRadius: 2, border: "1px solid rgba(255,255,255,0.12)" }}
      />
      <div className="flex gap-4 mt-2 text-xs text-muted">
        {Object.entries(KIND_COLOR).map(([k, c]) => (
          <span key={k} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: c }} />
            {k}
          </span>
        ))}
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full border border-danger" />
          flagged mule
        </span>
      </div>
    </div>
  );
}
