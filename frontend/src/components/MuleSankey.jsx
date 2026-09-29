import { useEffect, useRef } from "react";
import { sankey, sankeyLinkHorizontal } from "d3-sankey";
import { CHART_PALETTE, inr } from "../theme/tokens";

// Mule-migration Sankey: origin (complaint) state -> mule registration state.
export default function MuleSankey({ nodes, links, height = 360 }) {
  const wrapRef = useRef(null);
  const svgRef = useRef(null);

  useEffect(() => {
    if (!nodes?.length || !links?.length) return;
    const width = wrapRef.current?.clientWidth || 600;

    const idx = new Map(nodes.map((n, i) => [n.id, i]));
    const graph = {
      nodes: nodes.map((n) => ({ ...n })),
      links: links.map((l) => ({
        source: idx.get(l.source),
        target: idx.get(l.target),
        value: l.value,
        amount: l.amount,
      })),
    };

    const layout = sankey()
      .nodeWidth(14)
      .nodePadding(10)
      .extent([
        [1, 1],
        [width - 1, height - 6],
      ]);

    let g;
    try {
      g = layout(graph);
    } catch {
      return;
    }

    const linkPath = sankeyLinkHorizontal();
    const linksSvg = g.links
      .map((l, i) => {
        const c = CHART_PALETTE[i % CHART_PALETTE.length];
        return `<path d="${linkPath(l)}" fill="none" stroke="${c}" stroke-opacity="0.35" stroke-width="${Math.max(
          1,
          l.width
        )}"><title>${l.value} mules · ${inr(l.amount)}</title></path>`;
      })
      .join("");

    const nodesSvg = g.nodes
      .map((n) => {
        const label = n.label || n.id;
        const txtX = n.x0 < width / 2 ? n.x1 + 5 : n.x0 - 5;
        const anchor = n.x0 < width / 2 ? "start" : "end";
        return `<rect x="${n.x0}" y="${n.y0}" width="${n.x1 - n.x0}" height="${Math.max(
          1,
          n.y1 - n.y0
        )}" fill="#84E600" rx="2"/><text x="${txtX}" y="${
          (n.y0 + n.y1) / 2
        }" dy="0.35em" text-anchor="${anchor}" fill="#A3A39D" font-size="10">${label}</text>`;
      })
      .join("");

    svgRef.current.innerHTML = linksSvg + nodesSvg;
  }, [nodes, links, height]);

  return (
    <div ref={wrapRef} className="w-full overflow-x-auto">
      <svg ref={svgRef} width="100%" height={height} />
    </div>
  );
}
