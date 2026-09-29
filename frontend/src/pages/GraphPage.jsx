import { useEffect, useState } from "react";
import client from "../api/client";
import { Card, Skeleton, StatCard } from "../components/ui";
import NetworkGraph from "../components/NetworkGraph";
import MuleSankey from "../components/MuleSankey";

export default function GraphPage() {
  const [graph, setGraph] = useState(null);
  const [flow, setFlow] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    client
      .get("/graph")
      .then(({ data }) => setGraph(data))
      .catch((e) =>
        setError(e.response?.status === 403 ? "Restricted to LEA roles." : "Failed to load graph.")
      );
    client.get("/mule-flow").then(({ data }) => setFlow(data));
  }, []);

  if (error) {
    return (
      <Card title="Fraud Network Graph">
        <div className="text-sm text-danger">{error}</div>
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <div><h1 className="text-2xl font-bold tracking-tight">Fraud network</h1><p className="text-sm text-muted">Trace complaint-to-mule linkages without treating shared banks as syndicate evidence.</p></div>
      {graph && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Nodes" value={graph.stats.node_count} />
          <StatCard label="Edges" value={graph.stats.edge_count} />
          <StatCard label="Syndicates" value={graph.stats.component_count} tone="danger" />
          <StatCard label="Tracked mule flows" value={flow?.links?.length ?? "—"} tone="accent" />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <Card title="Cross-complaint syndicate graph">
            {!graph ? (
              <Skeleton className="h-96" />
            ) : (
              <NetworkGraph nodes={graph.nodes} edges={graph.edges} />
            )}
          </Card>
        </div>
        <Card title="Detected Syndicates">
          {!graph ? (
            <Skeleton className="h-96" />
          ) : (
            <div className="space-y-2 max-h-[520px] overflow-y-auto">
              {graph.syndicates.map((s) => (
                <div
                  key={s.syndicate_id}
                  className="bg-bg rounded-lg px-3 py-2 border border-danger/20"
                >
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Syndicate #{s.syndicate_id}</span>
                    <span className="text-xs text-muted">{s.size} nodes</span>
                  </div>
                  <div className="text-[11px] text-muted mt-0.5">
                    {s.mule_accounts} mule accounts · {s.complaints} linked complaints
                  </div>
                </div>
              ))}
              {!graph.syndicates.length && (
                <div className="text-sm text-muted">No syndicates ≥3 nodes detected.</div>
              )}
            </div>
          )}
        </Card>
      </div>

      <Card title="Mule migration flow (origin state → registration state)">
        {!flow ? (
          <Skeleton className="h-64" />
        ) : flow.links?.length ? (
          <MuleSankey nodes={flow.nodes} links={flow.links} />
        ) : (
          <div className="text-sm text-muted">No cross-state mule flow in scope.</div>
        )}
      </Card>
    </div>
  );
}
